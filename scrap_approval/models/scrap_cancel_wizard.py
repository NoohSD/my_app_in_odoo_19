from odoo import models, fields, _
from odoo.exceptions import UserError


class ScrapCancelWizard(models.TransientModel):
    _name = 'scrap.cancel.wizard'
    _description = 'Scrap Cancellation/Rejection Reason'

    scrap_ids = fields.Many2many(
        comodel_name='stock.scrap',
        string='Scrap Orders',
    )

    reason = fields.Text(
        string='Reason',
        required=True,
    )

    def action_confirm(self):
        if not self.reason:
            raise UserError(_('Please provide a reason.'))
        is_rejection = self.env.context.get('is_rejection', False)
        scraps = self.env['stock.scrap'].browse(
            self.env.context.get('default_scrap_ids', [])
        )
        new_state = 'rejected' if is_rejection else 'cancel'
        for rec in scraps:
            rec.sudo().write({
                'state': new_state,
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'cancellation_reason': self.reason,
                'approval_deadline': False,
            })
            rec.sudo()._message_log(
                body=_('❌ %s by %s.<br/>Reason: %s') % (
                    'Rejected' if is_rejection else 'Cancelled',
                    self.env.user.name,
                    self.reason,
                )
            )
        return {'type': 'ir.actions.act_window_close'}