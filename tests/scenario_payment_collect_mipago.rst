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
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, create_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> today = datetime.date.today()

Install account_invoice::

    >>> config = activate_modules('payment_collect_mipago')

Create company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'ar_cuit'
    >>> tax_identifier.code = '11111111113'
    >>> company.party.iva_condition = 'responsable_inscripto'
    >>> company.party.save()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]
    >>> period_ids = [p.id for p in fiscalyear.periods]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create tax::

    >>> TaxCode = Model.get('account.tax.code')
    >>> tax = create_tax(Decimal('.21'))
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

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.customer_taxes.append(tax)
    >>> account_category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('0')
    >>> template.account_category = account_category
    >>> template.save()
    >>> product, = template.products

Create invoices::

    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.invoice_date = period.start_date
    >>> invoice.paymode = paymode
    >>> line = invoice.lines.new()
    >>> line.product = product
    >>> line.quantity = 5
    >>> line.unit_price = Decimal('40')
    >>> invoice.click('post')
    >>> invoice.total_amount
    Decimal('220.00')
    >>> invoice = Invoice()
    >>> invoice.party = party 
    >>> invoice.invoice_date = period.start_date
    >>> invoice.paymode = paymode
    >>> line = invoice.lines.new()
    >>> line.product = product
    >>> line.quantity = 5
    >>> line.unit_price = Decimal('20')
    >>> invoice.click('post')
    >>> invoice.total_amount
    Decimal('110.00')

Configure mipago collect::

    >>> CollectConfig = Model.get('payment_collect.configuration')
    >>> collect_config = CollectConfig(1)
    >>> collect_config.payment_method_mipago = payment_method
    >>> collect_config.mipago_company_code = company.party.vat_number
    >>> collect_config.save()

Generate mipago collect::

    >>> Invoice = Model.get('account.invoice')
    >>> with file_open('payment_collect_mipago/tests/transactions.csv', 'rb') as f:
    ...     return_file = f.read()
    >>> Attachment = Model.get('ir.attachment')
    >>> payment_collect = Wizard('payment.collect.return')
    >>> payment_collect.form.period = period
    >>> payment_collect.form.paymode_type = 'payment.paymode.mipago'
    >>> payment_collect.form.return_file = return_file
    >>> payment_collect.execute('return_collect')
    >>> collect, = payment_collect.actions[0]
    >>> collect.monto_total
    Decimal('330.00')
    >>> collect.cantidad_registros == 2
    True
    >>> collect.period == period
    True
    >>> attachment = collect.attachments[1]
    >>> with file_open('payment_collect_mipago/tests/transactions.txt', 'rb') as f:
    ...     attachment.data == f.read()
    True
    >>> invoices = Invoice.find()
    >>> len(invoices)
    2
    >>> invoice = invoices[0]
    >>> invoice.state
    'paid'
    >>> invoice = invoices[1]
    >>> invoice.state
    'posted'
