# This file is part of the payment_collect_mipago module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import io
import csv
import logging
from decimal import Decimal

from trytond.model import ModelStorage
from trytond.pool import Pool
from trytond.modules.payment_collect.payments import PaymentMixIn

logger = logging.getLogger(__name__)

RETORNOS_MIPAGO = {
    'Pagado': 'Pagado',
    }
_SEPARATOR = ','


class PayModeMiPago(ModelStorage, PaymentMixIn):
    'Pay Mode MiPago'
    __name__ = 'payment.paymode.mipago'

    def return_collect(self, start):
        logger.info("return_collect: MiPago")
        super().return_collect(start, RETORNOS_MIPAGO)
        pool = Pool()
        Configuration = pool.get('payment_collect.configuration')
        Invoice = pool.get('account.invoice')
        CollectTransaction = pool.get('payment.collect.transaction')


        collect = self.attach_collect()
        collect.create_invoices_button = start.create_invoices
        collect.save()
        return [collect]

        config = Configuration(1)
        payment_method = config.payment_method
        if config.payment_method_mipago:
            payment_method = config.payment_method_mipago

        pay_date = pool.get('ir.date').today()

        data = io.StringIO(collect.attachments[0].data.decode('utf8'))
        reader = csv.DictReader(data, delimiter=_SEPARATOR)
        invoices = []
        for row in reader:
            if row.get('transaction_state', '') == 'Pagada':
                title, move = row.get('transaction_title', '').split('::')
                customer_identifier = row.get('customer_identifier')
                tr_paid_amount = Decimal(row.get('transaction_paid_amount'))
                try:
                    invoice, = Invoice.search([
                        ('state', '=', 'posted'),
                        ('move', '=', move),
                        ('party.code', '=', customer_identifier),
                        ])
                except ValueError:
                    logger.error('invoice move %s does not exists', move)

                if tr_paid_amount > invoice.total_amount:
                    # add credit with the difference
                    diff_amount = tr_paid_amount - invoice.total_amount
                    self.add_credit(invoice, diff_amount, payment_method)

                collect_tr = CollectTransaction(
                    collect_result='A',  # paid accepeted
                    collect_message='Pagada',
                    collect=collect,
                    pay_date=today,
                    pay_amount=invoice.total_amount,
                    payment_method=payment_method,
                    )
                invoice.collect_transactions += (collect_tr,)
                invoices.append(invoice)
            Invoice.save(invoices)

    @classmethod
    def add_credit(cls, invoice, amount, payment_method):
        pool = Pool()
        Move = pool.get('account.move')
        Period = pool.get('account.period')
        Date = pool.get('ir.date')

        today = Date.today()

        move = Move()
        move.period = Period.find(invoice.company, date=today)
        move.journal = payment_method.journal
        move.date = today

        line = move.lines.new()
        line.account = payment_method.debit_account
        line.debit = abs(amount)

        line = move.lines.new()
        line.account = invoice.account
        line.credit = abs(amount)
        line.party = invoice.party
        move.save()
