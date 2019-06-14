# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta
from trytond.model import fields

__all__ = ['Party', 'PartyIdentifier']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    @classmethod
    def copy(cls, parties, default=None):
        if default is None:
            default = {}
        default['identifiers'] = None
        return super(Party, cls).copy(parties, default=default)


class PartyIdentifier(metaclass=PoolMeta):
    __name__ = 'party.identifier'

    @classmethod
    def __setup__(cls):
        super(PartyIdentifier, cls).__setup__()
        for new_type in [
                ('mipago', 'MiPago'),
                ]:
            if new_type not in cls.type.selection:
                cls.type.selection.append(new_type)
        cls._error_messages.update({
                'unique_mipago': ('There is another party with the'
                    ' same code "%(code)s"'),
                })

    def check_unique_mipago(self):
        return self.search_count([
            ('code', '=', self.code),
            ('type', '=', 'mipago'),
            ('party', '!=', self.party),
            ('party.active', '=', True),
            ])

    @fields.depends('code', 'type')
    def pre_validate(self):
        super(PartyIdentifier, self).pre_validate()
        if (self.type == 'mipago' and self.code
                and self.check_unique_mipago() > 0):
            self.raise_user_error('unique_mipago', {
                    'code': self.code,
                    })
