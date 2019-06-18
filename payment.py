# This file is part of the payment_collect_mipago module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from datetime import datetime
from decimal import Decimal
from stdnum.ar import cbu

import logging
from trytond.pool import Pool
from trytond.modules.payment_collect.payments import PaymentMixIn
from trytond.model import ModelStorage
from trytond.transaction import Transaction
logger = logging.getLogger(__name__)

__all__ = ['PayModeMiPago']

RETORNOS_MIPAGO = {
    'Pagado': 'Pagado',
}


class PayModeMiPago(ModelStorage, PaymentMixIn):
    'Pay Mode MiPago'
    __name__ = 'payment.paymode.mipago'

    _SEPARATOR = ','
    _DEBITO_CODE = '51'
    _CREDITO_CODE = '53'

    @classmethod
    def __setup__(cls):
        super(PayModeMiPago, cls).__setup__()
        cls._error_messages.update({
                'missing_company_code':
                'Debe establecer el número de comercio en la configuración '
                'de contabilidad.',
                'missing_mipago_description':
                'Paymode description field is missing at invoice: "(%s)"',
                })

    def generate_collect(self, start):
        logger.info("generate_collect: mipago")
        pool = Pool()

        Company = pool.get('company.company')
        Attachment = pool.get('ir.attachment')
        Invoice = pool.get('account.invoice')
        Currency = pool.get('currency.currency')
        Configuration = pool.get('payment_collect.configuration')
        today = pool.get('ir.date').today()
        config = Configuration(1)
        if config.mipago_company_code:
            company_code = config.mipago_company_code
        else:
            self.raise_user_error('missing_company_code')
        self.period = start.period
        csv_format = start.csv_format
        self.monto_total = Decimal('0')
        self.cantidad_registros = 0
        self.type = 'send'
        self.filename = 'MAIN%s_%s.txt' % (company_code,
            today.strftime("%d%m"))
        format_number = self.get_format_number()
        format_date = self.get_format_date()
        domain = self.get_domain(start.period)
        domain.append(('paymode.type', '=', start.paymode_type))
        order = self.get_order()
        invoices = Invoice.search(domain, order=order)
        self.res = []
        self.monto_total = Decimal('0')
        self.cantidad_registros = 0
        for invoice in invoices:
            if invoice.paymode.bank_account:
                cbu_number = cbu.compact(invoice.paymode.bank_account.rec_name)
            else:
                cbu_number = invoice.paymode.cbu_number
            self.bcra_code = cbu_number[:3]
            if invoice.total_amount >= Decimal('0'):
                self.codigo_registro = self._DEBITO_CODE
            else:
                self.codigo_registro = self._CREDITO_CODE
            self.fecha_vencimiento = start.expiration_date.strftime("%y%m%d")
            self.empresa_credicoop = company_code.ljust(5, '0')
            self.client_number = invoice.party.code.rjust(10, '0').ljust(22)
            self.moneda = 'P'
            self.cbu_number = cbu_number.ljust(22)
            self.amount = Currency.round(invoice.currency,
                invoice.amount_to_pay)
            self.total_amount = self.amount.to_eng_string().replace('.',
                '').rjust(10, '0')
            self.monto_total = self.monto_total + self.amount
            self.cuit_company = invoice.company.party.vat_number
            if invoice.paymode.description:
                self.description = invoice.paymode.description.name.ljust(10)
                self.client_number = invoice.party.code.rjust(
                    invoice.paymode.description.positions, '0').ljust(22)
            else:
                self.raise_user_error('missing_mipago_description', invoice.id)
            self.vencimiento_dominio = str(invoice.id).ljust(15)
            self.res.append(self.a_texto(csv_format))
            self.cantidad_registros = self.cantidad_registros + 1

        collect = self.attach_collect()

        company = Company(Transaction().context.get('company'))
        remito_info = """
        Nombre Empresa: %s
        Fecha de Vto: %s, Cant. Ditos: %s, Importe Total: %s
        """ % (company.party.name, format_date(start.expiration_date),
            self.cantidad_registros, format_number(self.monto_total))
        remito = Attachment()
        remito.name = 'REMITO.txt'
        remito.resource = collect
        remito.data = remito_info.encode('utf8')
        remito.save()

        return [collect]

    def lista_campo_ordenados(self):
        """ Devuelve lista de campos ordenados """
        return [
            self.bcra_code,
            self.codigo_registro,
            self.fecha_vencimiento,
            self.empresa_credicoop,
            self.client_number,
            self.moneda,
            self.cbu_number,
            self.total_amount,
            self.cuit_company,
            self.description,
            self.vencimiento_dominio,
            ]

    def return_collect(self, start):
        super(PayModeMiPago, self).return_collect(start, RETORNOS_MIPAGO)
        collect = self.attach_collect()
        collect.create_invoices_button = True
        collect.save()
        return [collect]
