=============================
Payment Collect BCCL Scenario
=============================

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

    >>> config = activate_modules('payment_collect_bccl')

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
    >>> tax = create_tax(Decimal('.10'))
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
    >>> payment_method.name = 'Cash'
    >>> payment_method.journal = journal_cash
    >>> payment_method.credit_account = account_cash
    >>> payment_method.debit_account = account_cash
    >>> payment_method.save()

Create desc BCCL::

    >>> DescPayModeBCCL = Model.get('payment.paymode.bccl.desc')
    >>> desc_bccl = DescPayModeBCCL()
    >>> desc_bccl.name = 'SERVICE'
    >>> desc_bccl.positions =10
    >>> desc_bccl.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create a bank::

    >>> Bank = Model.get('bank')
    >>> bank = Bank()
    >>> bank.party = party
    >>> bank.save()

Create bank account::

    >>> Account = Model.get('bank.account')
    >>> Number = Model.get('bank.account.number')
    >>> account = Account()
    >>> account.bank = bank
    >>> account.journal = journal_cash
    >>> account.credit_account = account_cash 
    >>> account.debit_account = account_cash
    >>> account.owners.append(party)
    >>> number = Number()
    >>> number.type = 'cbu'
    >>> number.number = '2850590940090418135201'
    >>> account.numbers.append(number)
    >>> account.save()
    >>> cbu_number, = account.numbers
    >>> cbu_number.number_compact
    '2850590940090418135201'

Create paymode method::

    >>> Paymode = Model.get('payment.paymode')
    >>> paymode = Paymode()
    >>> paymode.party = party
    >>> paymode.type = 'payment.paymode.bccl'
    >>> paymode.cbu_number = cbu_number.number_compact
    >>> paymode.bank_account = account
    >>> paymode.description = desc_bccl
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
    >>> template.list_price = Decimal('40')
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

Configure bccl collect::

    >>> CollectConfig = Model.get('payment_collect.configuration')
    >>> collect_config = CollectConfig(1)
    >>> collect_config.journal_bccl = journal_cash
    >>> collect_config.bccl_company_code = '314'
    >>> collect_config.save()

Generate bccl collect::

    >>> Attachment = Model.get('ir.attachment')
    >>> payment_collect = Wizard('payment.collect.send')
    >>> payment_collect.form.csv_format = False
    >>> payment_collect.form.period = period
    >>> payment_collect.form.expiration_date = datetime.date(2019, 12, 31)
    >>> payment_collect.form.paymode_type = 'payment.paymode.bccl'
    >>> payment_collect.execute('generate_collect')
    >>> collect, = payment_collect.actions[0]
    >>> collect.monto_total
    Decimal('330.00')
    >>> collect.cantidad_registros == 2
    True
    >>> collect.period == period
    True
    >>> filename = 'MAIN314_%s.txt' % today.strftime("%d%m")
    >>> attachment = collect.attachments[1]
    >>> with file_open('payment_collect_bccl/tests/MAIN.txt', 'rb') as f:
    ...     attachment.data == f.read()
    True
