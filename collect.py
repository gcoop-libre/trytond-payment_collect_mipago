# This file is part of the payment_collect_mipago module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import io
import csv
import logging
from decimal import Decimal, ROUND_HALF_EVEN

from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, ModelView
from trytond.transaction import Transaction
from trytond.bus import notify

__all__ = ['Collect', 'CollectReturnStart']
logger = logging.getLogger(__name__)


class Collect(metaclass=PoolMeta):
    __name__ = 'payment.collect'

    @classmethod
    def _create_invoices(cls, collects):

        def round(amount, rounding=ROUND_HALF_EVEN):
            'Round the amount depending of the price_digits'
            digits = Decimal('0.0001')
            return (amount / digits).quantize(Decimal('1.'),
                    rounding=rounding) * digits

        pool = Pool()
        AccountConfig = pool.get('account.configuration')
        Account = pool.get('account.account')
        Address = pool.get('party.address')
        ContactMechanism = pool.get('party.contact_mechanism')
        CollectTransaction = pool.get('payment.collect.transaction')
        Company = pool.get('company.company')
        Configuration = pool.get('payment_collect.configuration')
        Invoice = pool.get('account.invoice')
        InvoiceLine = pool.get('account.invoice.line')
        Party = pool.get('party.party')
        PartyIdentifier = pool.get('party.identifier')
        Tax = pool.get('account.tax')
        Date = pool.get('ir.date')
        config = Configuration(1)
        payment_method = config.payment_method
        if config.payment_method_mipago:
            payment_method = config.payment_method_mipago
        parties = []
        all_invoices = []
        to_create = []
        to_update = []
        account_config = AccountConfig(1)
        account_revenue = account_config.default_category_account_revenue
        tax_iva_21, = Tax.search([
                ('group.afip_kind', '=', 'gravado'),
                ('iva_code', '=', '5'),
                ('group.kind', 'in', ('sale', 'both')),
                ])
        today = Date.today()
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            currency = company.currency
        notify('Creando comprobantes')
        for collect in collects:
            if (collect.create_invoices_button and
                    collect.paymode_type == 'payment.paymode.mipago'):
                # create parties
                data = io.StringIO(collect.attachments[0].data.decode('utf8'))
                reader = csv.DictReader(data, delimiter=',')
                for row in reader:
                    try:
                        party, = Party.search([
                                ('identifiers.type', '=', 'mipago'),
                                ('identifiers.code', '=',
                                    row.get('customer_email')),
                                ])
                    except ValueError:
                        logger.info('customer_email %s do not exists' %
                            row.get('customer_email'))
                        party = Party(
                            name=row.get('customer_name'),
                            iva_condition='consumidor_final',
                            identifiers=[
                                PartyIdentifier(type='mipago',
                                    code=row.get('customer_email'))
                                ],
                            contact_mechanisms=[
                                ContactMechanism(type='email', value=row.get('customer_email'),
                                    invoice=True),
                                ],
                            addresses=[
                                Address(invoice=True),
                                ])
                        party.save()

                    found_invoices = Invoice.search([
                        ('reference', '=', row.get('transaction_id')),
                        ])
                    if found_invoices:
                        invoice, = found_invoices
                        if invoice.state in ['posted', 'paid', 'canceled']:
                            continue
                        to_update.append(invoice)
                        total_amount = invoice.total_amount
                    else:
                        # create invoice
                        invoice = Invoice()
                        invoice.type = 'out'
                        invoice.party = party
                        invoice.on_change_type()
                        invoice.on_change_party()
                        invoice.company = company
                        invoice.currency = company.currency
                        invoice.state = 'draft'
                        invoice.pos = collect.pos
                        invoice.on_change_pos()
                        invoice.invoice_type = collect.invoice_type
                        invoice.reference = row.get('transaction_id')
                        invoice.taxes = ()
                        total_amount = Decimal(
                            row.get('transaction_amount'))
                        untaxed_unit_price = total_amount / Decimal('1.21')
                        invoice_line = InvoiceLine(
                            invoice_type='out',
                            type='line',
                            description='DONACION',
                            account=account_revenue,
                            quantity=1.0,
                            unit_price=round(untaxed_unit_price),
                            taxes=(tax_iva_21,),
                            )
                        taxes = [tax_iva_21]
                        pattern = invoice_line._get_tax_rule_pattern()
                        party = invoice.party
                        if party.customer_tax_rule:
                            tax_ids = party.customer_tax_rule.apply(None, pattern)
                            if tax_ids:
                                taxes.extend(tax_ids)
                        invoice_line.taxes = taxes
                        invoice.lines = [invoice_line]
                        invoice.pyafipws_concept = '2'
                        invoice.set_pyafipws_billing_dates()
                        to_create.append(invoice)

                    if (invoice.state != 'paid' and
                            row.get('transaction_state') == 'Pagada'):
                            collect_tr = CollectTransaction(
                                collect_result='A', # paid accepeted
                                collect_message=row.get('transaction_state'),
                                collect=collect,
                                pay_date=today,
                                pay_amount=total_amount,
                                payment_method=payment_method,
                                )
                    elif (invoice.state != 'paid' and
                            row.get('transaction_state') != 'Pagada'):
                            collect_tr = CollectTransaction(
                                collect_result='R', # paid pending
                                collect_message=row.get('transaction_state'),
                                collect=collect,
                                pay_date=today,
                                pay_amount=total_amount,
                                payment_method=payment_method,
                                )
                    if collect_tr and found_invoices:
                        invoice.collect_transactions += (collect_tr,)
                    elif collect_tr:
                        invoice.collect_transactions = collect_tr,
                    all_invoices.append(invoice)
                Invoice.save(all_invoices)
                Invoice.validate_invoice(all_invoices)
                notify('Se crearon %s comprobantes' % len(all_invoices))


class CollectReturnStart(metaclass=PoolMeta):
    __name__ = 'payment.collect.return.start'

    @property
    def origin_name(self):
        pool = Pool()
        PayModeMiPago = pool.get('payment.paymode.mipago')
        name = super(PayModeMiPago, self).origin_name
        if isinstance(self.origin, PayModeMiPago):
            name = self.origin.paymode.rec_name
        return name

    @classmethod
    def _get_origin(cls):
        models = super(CollectReturnStart, cls)._get_origin()
        models.append('payment.paymode.mipago')
        return models
