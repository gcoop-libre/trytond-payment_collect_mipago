# This file is part of the payment_collect_mipago module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import io
import csv
import logging
from decimal import Decimal

from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, ModelView
from trytond.transaction import Transaction

__all__ = ['Collect', 'CollectReturnStart']
logger = logging.getLogger(__name__)


class Collect(metaclass=PoolMeta):
    __name__ = 'payment.collect'

    @classmethod
    @ModelView.button
    @Workflow.transition('processing')
    def create_invoices(cls, collects):
        pool = Pool()
        Account = pool.get('account.account')
        Address = pool.get('party.address')
        CollectTransaction = pool.get('payment.collect.transaction')
        Company = pool.get('company.company')
        Configuration = pool.get('payment_collect.configuration')
        Country = pool.get('country.country')
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
        account_revenue, = Account.search([
            ('kind', '=', 'revenue'),
            ('code', '=', '511'),
            ])
        ar, = Country.search([('code', '=', 'AR')])
        tax_iva_21, = Tax.search([
                ('name', '=', 'IVA Ventas 21%'),
                ])
        today = Date.today()
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            currency = company.currency
        for collect in collects:
            if collect.create_invoices_button:
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
                        party = Party(name=row.get('customer_name'),
                            iva_condition='consumidor_final',
                            identifiers=[PartyIdentifier(type='mipago',
                                    code=row.get('customer_email'))],
                            addresses=[Address(country=ar)])
                        party.save()

                    found_invoices = Invoice.search([
                        ('reference', '=', row.get('transaction_id')),
                        ])
                    if found_invoices:
                        invoice, = found_invoices
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
                        invoice.invoice_type = invoice.on_change_with_invoice_type()
                        invoice.set_pyafipws_concept()
                        invoice.set_pyafipws_billing_dates()
                        invoice.reference = row.get('transaction_id')
                        invoice.taxes = ()
                        total_amount = currency.round(Decimal(row.get(
                                'transaction_first_overdue_amount')))
                        untaxed_unit_price = total_amount / Decimal('1.21')
                        invoice_line = InvoiceLine(
                            invoice_type='out',
                            type='line',
                            description='',
                            account=account_revenue,
                            quantity=1.0,
                            unit_price=currency.round(untaxed_unit_price),
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

                    if (invoice.state != 'paid' and
                            row.get('transaction_state') == 'Pagada'):
                            collect_tr = CollectTransaction(
                                collect_result='A', # paid accepeted
                                collect_message=row.get('transaction_state'),
                                collect=collect,
                                pay_date=today,
                                pay_amount=invoice.total_amount,
                                payment_method=payment_method,
                                )
                    elif (invoice.state != 'paid' and
                            row.get('transaction_state') != 'Pagada'):
                            collect_tr = CollectTransaction(
                                collect_result='R', # paid pending
                                collect_message=row.get('transaction_state'),
                                collect=collect,
                                pay_date=today,
                                pay_amount=invoice.total_amount,
                                payment_method=payment_method,
                                )
                    if collect_tr and found_invoices:
                        invoice.collect_transactions += (collect_tr,)
                    elif collect_tr:
                        invoice.collect_transactions = collect_tr,
                    all_invoices.append(invoice)
                save_invoices = [i for i in all_invoices if i.state in ['draft', 'validated']]
                Invoice.save(save_invoices)
                update_invoices = (i for i in save_invoices if i.state == 'draft')
                Invoice.update_taxes(update_invoices)
                Invoice.validate_invoice(all_invoices)
        super(Collect, cls).create_invoices(collects)


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
