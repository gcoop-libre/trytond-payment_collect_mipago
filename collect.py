# This file is part of the payment_collect_mipago module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import PoolMeta, Pool

__all__ = ['Collect', 'CollectReturnStart']


class Collect(metaclass=PoolMeta):

    @classmethod
    def read_return_file(cls, collect):
        # read return file.
        reader = csv.DictReader(collect.return_file, delimiter=',')
        return reader

    @classmethod
    def create_invoices(cls, collects):
        # customer_identifier,customer_email,customer_name,company_name,company_CUIT,transaction_title,transaction_state,transaction_creation_date,transaction_first_overdue_amount,transaction_second_overdue_amount,payment_amounts_sum
        # 1,cliente1@gcoop.coop,"Cliente 1","Test 1",20353172558,"Test 1",Pendiente,2019-05-30,100.00,,
        # 2,cliente2@gcoop.coop,"Cliente 2","Test 1",20353172558,"Test 1",Pagada,2019-05-30,100.00,,20.10
        # se itera por el archivo y genero relaciones con las facturas.

        pool = Pool()
        Invoice = pool.get('account.invoice')
        Party = pool.get('party.party')
        PartyIdentifier = pool.get('party.identifier')
        Account = pool.get('account.account')
        CollectTransaction = pool.get('payment.collect.transaction')
        Configuration = Pool().get('payment_collect.configuration')
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
        for collect in collects:
            if collect.create_invoices:
                # create parties
                reader = cls.read_return_file(collect)
                for line in reader:
                    party = Party(name=line.get('customer_name'))
                    party.identifiers.append(PartyIdentifier(type='mipago',
                        code=line.get('customer_email')))
                    try:
                        party.save()
                    except UserError:
                        logger.info('customer_email %s exists' %
                            line.get('customer_email'))
                        party, = Party.search([('identifiers.code', '=',
                                    line.get('customer_email'))])

                    invoices = Invoice.search([
                        ('reference', '=', line.get('transaction_id')),
                        ('state', '!=', 'cancel'),
                        ])
                    if invoices:
                        invoice, = invoices
                    else:
                        # create invoice
                        invoice = Invoice()
                        invoice.type = 'out'
                        invoice.party = party
                        invoice.on_change_type()
                        invoice.on_change_party()
                        invoice.state = 'draft'
                        # invoice.pos = pos
                        # invoice.on_change_pos()
                        # invoice.invoice_type = invoice.on_change_with_invoice_type()
                        # invoice.pyafipws_concept = '1'
                        # invoice.set_pyafipws_billing_dates()
                        invoice.lines.append(InvoiceLine(
                                account=account_revenue,
                                description='',
                                quantity=1.0,
                                unit_price=Decimal(line.get(
                                        'transaction_first_overdue_amount')),
                                ))
                        # FIXME: add taxes
                        # invoice.lines.taxes.append(Tax(name='IVA 21%'))
                    if (invoice.state != 'paid' and
                            invoice.line.get('transaction_state') == 'Pagada'):
                        invoice.collect_transactions.append(
                            CollectTransaction(
                                collect_result='A', # paid accepeted
                                collect_message=line.get('transaction_state'),
                                collect=collect,
                                pay_date=today,
                                pay_amount=Decimal(line.get(
                                    'transaction_first_overdue_amount')),
                                payment_method=payment_method,
                                ))
                    elif (invoice.state != 'paid' and
                            invoice.line.get('transaction_state') != 'Pagada'):
                        invoice.collect_transactions.append(
                            CollectTransaction(
                                collect_result='P', # paid pending
                                collect_message=line.get('transaction_state'),
                                collect=collect,
                                pay_date=today,
                                pay_amount=Decimal(line.get(
                                    'transaction_first_overdue_amount')),
                                payment_method=payment_method,
                                ))
                    invoices.append(invoice)
                Invoice.save(invoices)
                Invoice.validate_invoice(invoices)
        super(Collect, cls).create_invoices()


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

        Invoice = Pool().get('account.invoice')
        Configuration = Pool().get('payment_collect.configuration')
        config = Configuration(1)
        payment_method = None
        if config.payment_collect_mipago:
            payment_method = config.payment_method_mipago
