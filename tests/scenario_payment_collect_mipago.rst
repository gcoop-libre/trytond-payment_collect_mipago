===============================
Payment Collect MiPago Scenario
===============================

Imports::
    >>> import datetime
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.tools import file_open
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.currency.tests.tools import get_currency
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, create_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> from trytond.modules.account_invoice_ar.tests.tools import \
    ...     create_pos, get_invoice_types, get_pos, create_tax_groups, \
    ...     set_afip_certs
    >>> from trytond.modules.account_invoice_ar.afip_auth import \
    ...     authenticate, get_cache_dir
    >>> from pyafipws.wsfev1 import WSFEv1
    >>> import pytz
    >>> timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    >>> today = datetime.datetime.now(timezone).date()
    >>> year = datetime.date(2019, 1, 1)

Install account_invoice::

    >>> config = activate_modules('payment_collect_mipago')

Create company::

    >>> currency = get_currency('ARS')
    >>> currency.afip_code = 'PES'
    >>> currency.save()
    >>> _ = create_company(currency=currency)
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'ar_cuit'
    >>> tax_identifier.code = '30710158254' # gcoop CUIT
    >>> company.party.iva_condition = 'responsable_inscripto'
    >>> company.party.save()

Configure company timezone::

    >>> company.timezone = 'America/Argentina/Buenos_Aires'
    >>> company.save()

Configure AFIP certificates::

    >>> _ = set_afip_certs(company=company)

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create point of sale::

    >>> _ = create_pos(company, type='electronic', number=4000, ws='wsfe')
    >>> pos = get_pos(type='electronic', number=4000)
    >>> invoice_types = get_invoice_types(pos=pos)

Create tax groups::

    >>> tax_groups = create_tax_groups()

Create tax::

    >>> TaxCode = Model.get('account.tax.code')
    >>> tax = create_tax(Decimal('.21'))
    >>> tax.group = tax_groups['gravado']
    >>> tax.iva_code = '5'
    >>> tax.save()
    >>> invoice_base_code = create_tax_code(tax, 'base', 'invoice')
    >>> invoice_base_code.save()
    >>> invoice_tax_code = create_tax_code(tax, 'tax', 'invoice')
    >>> invoice_tax_code.save()
    >>> credit_note_base_code = create_tax_code(tax, 'base', 'credit')
    >>> credit_note_base_code.save()
    >>> credit_note_tax_code = create_tax_code(tax, 'tax', 'credit')
    >>> credit_note_tax_code.save()

Create payment method::

    >>> Journal = Model.get('account.journal')
    >>> PaymentMethod = Model.get('account.invoice.payment.method')
    >>> Sequence = Model.get('ir.sequence')
    >>> journal_cash, = Journal.find([('type', '=', 'cash')])
    >>> payment_method = PaymentMethod()
    >>> payment_method.name = 'Cobranza MiPago'
    >>> payment_method.journal = journal_cash
    >>> payment_method.credit_account = account_cash
    >>> payment_method.debit_account = account_cash
    >>> payment_method.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> identifier = party.identifiers.new()
    >>> identifier.type = 'mipago'
    >>> identifier.code = 'tryton@example.org'
    >>> party.save()

Create paymode method::

    >>> Paymode = Model.get('payment.paymode')
    >>> paymode = Paymode()
    >>> paymode.party = party
    >>> paymode.type = 'payment.paymode.mipago'
    >>> paymode.save()

SetUp webservice AFIP::

    >>> URL_WSAA = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
    >>> URL_WSFEv1 = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
    >>> certificate = str(company.pyafipws_certificate)
    >>> private_key = str(company.pyafipws_private_key)
    >>> cache = get_cache_dir()
    >>> auth_data = authenticate('wsfe', certificate, private_key,
    ...     cache=cache, wsdl=URL_WSAA)
    >>> wsfev1 = WSFEv1()
    >>> wsfev1.Cuit = company.party.vat_number
    >>> wsfev1.Token = auth_data['token']
    >>> wsfev1.Sign = auth_data['sign']
    >>> wsfev1.Conectar(wsdl=URL_WSFEv1, cache=cache)
    True

Get CompUltimoAutorizado and configure sequences::

    >>> #cbte_nro = int(wsfev1.CompUltimoAutorizado('1', pos.number))
    >>> #invoice_types['1'].invoice_sequence.number_next = cbte_nro + 1
    >>> #invoice_types['1'].invoice_sequence.save()

    >>> #cbte_nro = int(wsfev1.CompUltimoAutorizado('3', pos.number))
    >>> #invoice_types['3'].invoice_sequence.number_next = cbte_nro + 1
    >>> #invoice_types['3'].invoice_sequence.save()

    >>> cbte_nro = int(wsfev1.CompUltimoAutorizado('6', pos.number))
    >>> invoice_types['6'].invoice_sequence.number_next = cbte_nro + 1
    >>> invoice_types['6'].invoice_sequence.save()

    >>> #cbte_nro = int(wsfev1.CompUltimoAutorizado('11', pos.number))
    >>> #invoice_types['11'].invoice_sequence.number_next = cbte_nro + 1
    >>> #invoice_types['11'].invoice_sequence.save()

Configure mipago collect::

    >>> CollectConfig = Model.get('payment_collect.configuration')
    >>> collect_config = CollectConfig(1)
    >>> collect_config.payment_method_mipago = payment_method
    >>> collect_config.mipago_company_code = company.party.vat_number
    >>> collect_config.pos = pos
    >>> collect_config.save()

Configure account configuration::

    >>> AccountConfig = Model.get('account.configuration')
    >>> account_config = AccountConfig(1)
    >>> account_config.default_category_account_revenue = revenue
    >>> account_config.default_category_account_expense = expense
    >>> account_config.save()

Generate mipago collect::

    >>> Invoice = Model.get('account.invoice')
    >>> with file_open('payment_collect_mipago/tests/transactions.csv', 'rb') as f:
    ...     return_file = f.read()
    >>> Attachment = Model.get('ir.attachment')
    >>> payment_collect = Wizard('payment.collect.return')
    >>> payment_collect.form.paymode_type = 'payment.paymode.mipago'
    >>> payment_collect.form.return_file = return_file
    >>> payment_collect.form.create_invoices = True
    >>> payment_collect.execute('return_collect')
    >>> collect, = payment_collect.actions[0]
    >>> collect.pos.number
    4000
    >>> collect.invoice_type = invoice_types['6']
    >>> collect.state
    'processing'
    >>> # collect.monto_total
    # Decimal('330.00')
    >>> # collect.cantidad_registros == 2
    # True
    >>> attachment = collect.attachments[0]
    >>> with file_open('payment_collect_mipago/tests/transactions.csv', 'rb') as f:
    ...     attachment.data == f.read()
    True
    >>> collect.click('create_invoices')
    >>> collect.reload()
    >>> invoices = Invoice.find()
    >>> len(invoices)
    2
    >>> invoice = invoices[0]
    >>> invoice.state
    'validated'
    >>> collect.click('post_invoices')
    >>> invoice.reload()
    >>> invoice.state
    'posted'
    >>> collect.click('pay_invoices')
    >>> invoice.reload()
    >>> invoice.state
    'paid'
