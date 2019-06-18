# This file is part of the payment_collect_mipago module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import PoolMeta, Pool
from trytond.modules.company.model import CompanyValueMixin

__all__ = ['Configuration', 'ConfigurationPaymentCollectMiPago']


class Configuration(metaclass=PoolMeta):
    __name__ = 'payment_collect.configuration'
    payment_method_mipago = fields.MultiValue(fields.Many2One(
            'account.invoice.payment.method', "Payment Method Mi Pago",
            required=True))
    mipago_company_code = fields.MultiValue(fields.Char('Comany code MiPago'))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'mipago_company_code':
            return pool.get('payment_collect.configuration.mipago')
        elif field == 'payment_method_mipago':
            return pool.get('payment_collect.configuration.mipago')
        return super(Configuration, cls).multivalue_model(field)


class ConfigurationPaymentCollectMiPago(ModelSQL, CompanyValueMixin):
    "PaymentCollect Configuration BCCl"
    __name__ = 'payment_collect.configuration.mipago'

    payment_method_mipago = fields.Many2One('account.invoice.payment.method',
        "Payment Method MiPago")
    mipago_company_code = fields.Char('Compay code MiPago')
