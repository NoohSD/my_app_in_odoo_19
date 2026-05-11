# -*- coding: utf-8 -*-
{
    'name': 'Scrap Approval Workflow',
    'version': '19.0.1.0.0',
    'author': 'Nooh Suliman',
    'website': 'https://www.linkedin.com/in/nooh-suliman/',
    'summary': 'Add approval workflow to scrap orders with manager control and access restrictions',
    'description': """
Scrap Approval Workflow
=======================
This module adds a full approval workflow to Odoo's native scrap orders,
ensuring all scrap transactions are reviewed and approved by the
Scrap Operations Manager before being processed.

Key Features:
-------------
- Structured approval workflow (Draft > Waiting Approval > Done / Cancelled)
- Dedicated Scrap Operations Manager security group
- Record-level access control — each employee sees only their own orders
- Automatic manager notifications on submission
- Full approval tracking (approved by, approval date)
- Owner tracking — captures who created each scrap order
- Validation protection — standard Validate button removed
- Manager notes field for remarks before decision
- Reset to Draft for cancelled orders

Perfect for:
------------
- Inventory control
- Scrap transaction auditing
- Warehouse operations

    """,
    'depends': ['stock'],
    'data': [
       'security/groups.xml',
       'security/ir.model.access.csv',
       'security/scrap_security.xml',
       'views/scrap_cancel_wizard_views.xml',
       'views/stock_scrap_views.xml',
       'data/ir_cron.xml',
    ],
    'images': ['static/description/banner.png'],
    'icon': 'static/description/icon.png',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 10,
    'currency': 'USD',
    'application': False,
}
