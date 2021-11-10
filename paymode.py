# This file is part of the payment_collect_mipago module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pyson import Eval
from trytond.pool import PoolMeta, Pool

__all__ = ['PayMode']


class PayMode(metaclass=PoolMeta):
    __name__ = 'payment.paymode'

    @property
    def origin_name(self):
        pool = Pool()
        PayModeMiPago = pool.get('payment.paymode.mipago')
        name = super().origin_name
        if isinstance(self.origin, PayModeMiPago):
            name = self.origin.paymode.rec_name
        return name

    @classmethod
    def _get_origin(cls):
        models = super()._get_origin()
        models.append('payment.paymode.mipago')
        return models
