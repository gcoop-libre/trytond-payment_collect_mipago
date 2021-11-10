# This file is part of the payment_collect_mipago module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, fields
from trytond.pool import PoolMeta, Pool
from trytond.modules.company.model import CompanyValueMixin


class Configuration(metaclass=PoolMeta):
    __name__ = 'payment_collect.configuration'

    payment_method_mipago = fields.MultiValue(fields.Many2One(
        'account.invoice.payment.method', "MiPago Payment Method"))
    mipago_company_code = fields.MultiValue(fields.Char('MiPago Company code'))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in ['payment_method_mipago', 'mipago_company_code']:
            return pool.get('payment_collect.configuration.mipago')
        return super().multivalue_model(field)


class ConfigurationPaymentCollectMiPago(ModelSQL, CompanyValueMixin):
    "Payment Collect MiPago Configuration"
    __name__ = 'payment_collect.configuration.mipago'

    payment_method_mipago = fields.Many2One('account.invoice.payment.method',
        "MiPago Payment Method")
    mipago_company_code = fields.Char('MiPago Company code')
