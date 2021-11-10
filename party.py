# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.exceptions import UserError
from trytond.i18n import gettext


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    @classmethod
    def copy(cls, parties, default=None):
        if default is None:
            default = {}
        default['identifiers'] = None
        return super().copy(parties, default=default)


class PartyIdentifier(metaclass=PoolMeta):
    __name__ = 'party.identifier'

    @classmethod
    def get_types(cls):
        types = super().get_types()
        return types + [('mipago', 'MiPago')]

    @fields.depends('code', 'type')
    def pre_validate(self):
        super().pre_validate()
        self.check_unique_mipago()

    def check_unique_mipago(self):
        if self.type == 'mipago' and self.code:
            if self.search_count([
                    ('code', '=', self.code),
                    ('type', '=', 'mipago'),
                    ('party', '!=', self.party),
                    ('party.active', '=', True),
                    ]) > 0:
                raise UserError(gettext(
                    'payment_collect_mipago.msg_unique_mipago',
                    code=self.code))
