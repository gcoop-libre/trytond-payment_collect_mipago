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
        # customer_identifier,customer_email,customer_name,company_name,company_CUIT,transaction_title,transaction_state,transaction_creation_date,transaction_first_overdue_amount,transaction_second_overdue_amount,payment_amounts_sum
        # 1,cliente1@gcoop.coop,"Cliente 1","Test 1",20353172558,"Test 1",Pendiente,2019-05-30,100.00,,
        # 2,cliente2@gcoop.coop,"Cliente 2","Test 1",20353172558,"Test 1",Pagada,2019-05-30,100.00,,20.10
        # se itera por el archivo y genero relaciones con las facturas.

        pool = Pool()
        Invoice = pool.get('account.invoice')
        InvoiceLine = pool.get('account.invoice.line')
        Party = pool.get('party.party')
        Address = pool.get('party.address')
        Country = pool.get('country.country')
        PartyIdentifier = pool.get('party.identifier')
        Account = pool.get('account.account')
        CollectTransaction = pool.get('payment.collect.transaction')
        Configuration = Pool().get('payment_collect.configuration')
        Date = Pool().get('ir.date')
        config = Configuration(1)
        payment_method = config.payment_method
        if config.payment_method_mipago:
            payment_method = config.payment_method_mipago
        parties = []
        invoices = []
        account_revenue, = Account.search([
            ('kind', '=', 'revenue'),
            ('code', '=', '511'),
            ])
        ar, = Country.search([('code', '=', 'AR')])
        today = Date.today()
        company = Transaction().context.get('company')
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
                        ('state', '!=', 'cancel'),
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
                        #invoice.currency = company.currency
                        invoice.state = 'draft'
                        invoice.pos = collect.pos
                        invoice.on_change_pos()
                        invoice.invoice_type = invoice.on_change_with_invoice_type()
                        invoice.set_pyafipws_concept()
                        invoice.set_pyafipws_billing_dates()
                        invoice.reference = row.get('transaction_id')
                        invoice_line = InvoiceLine(
                                invoice_type = 'out',
                                type = 'line',
                                account=account_revenue,
                                quantity=1.0,
                                unit_price=Decimal(row.get(
                                        'transaction_first_overdue_amount')),
                                )
                        invoice.lines = [invoice_line]

                        # FIXME: add taxes
                        # invoice.lines.taxes.append(Tax(name='IVA 21%'))
                    if (invoice.state != 'paid' and
                            row.get('transaction_state') == 'Pagada'):
                            collect_tr = CollectTransaction(
                                collect_result='A', # paid accepeted
                                collect_message=row.get('transaction_state'),
                                collect=collect,
                                pay_date=today,
                                pay_amount=Decimal(row.get(
                                    'transaction_first_overdue_amount')),
                                payment_method=payment_method,
                                )
                    elif (invoice.state != 'paid' and
                            row.get('transaction_state') != 'Pagada'):
                            collect_tr = CollectTransaction(
                                collect_result='P', # paid pending
                                collect_message=row.get('transaction_state'),
                                collect=collect,
                                pay_date=today,
                                pay_amount=Decimal(row.get(
                                    'transaction_first_overdue_amount')),
                                payment_method=payment_method,
                                )
                    if collect_tr:
                        invoice.collect_transactions = [collect_tr]
                    invoices.append(invoice)
                Invoice.save(invoices)
                Invoice.validate_invoice(invoices)
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
