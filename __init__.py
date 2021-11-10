# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import paymode
from . import payment
from . import collect
from . import configuration
from . import party


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationPaymentCollectMiPago,
        paymode.PayMode,
        payment.PayModeMiPago,
        collect.Collect,
        collect.CollectReturnStart,
        party.Party,
        party.PartyIdentifier,
        module='payment_collect_mipago', type_='model')
