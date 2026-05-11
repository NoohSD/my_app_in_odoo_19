from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
import datetime


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    state = fields.Selection(
        selection_add=[
            ('waiting_approval', 'Waiting Approval'),
            ('cancel', 'Cancelled'),
            ('rejected', 'Rejected'),
        ],
        ondelete={
            'waiting_approval': 'cascade',
            'cancel': 'cascade',
            'rejected': 'cascade',
        },
    )

    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True,
        context={'no_check_company': True},
    )

    approved_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False,
    )

    approval_note = fields.Text(
        string='Order Notes',
    )

    cancellation_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        copy=False,
    )

    approval_deadline = fields.Datetime(
        string='Approval Deadline',
        readonly=True,
        copy=False,
    )

    owner_id = fields.Many2one(
        comodel_name='res.users',
        string='Owner',
        compute='_compute_owner_id',
        store=True,
        readonly=True,
        copy=False,
    )

    @api.depends('create_uid')
    def _compute_owner_id(self):
        for rec in self:
            rec.with_context(no_check_company=True).owner_id = rec.sudo().create_uid

    def action_validate(self):
        for rec in self:
            if rec.state == 'draft':
                raise UserError(_('Please submit the scrap order for approval before validating.'))
            if rec.state in ('cancel', 'rejected'):
                raise UserError(_('Cannot validate a cancelled or rejected scrap order.'))
            if rec.product_id and rec.location_id:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', '=', rec.location_id.id),
                ], limit=1)
                available_qty = quant.quantity if quant else 0.0
                if rec.scrap_qty > available_qty:
                    raise UserError(_(
                        'Cannot validate: requested quantity (%s %s) exceeds available stock (%s %s). '
                        'Please adjust the quantity before proceeding.'
                    ) % (
                        rec.scrap_qty,
                        rec.product_uom_id.name,
                        available_qty,
                        rec.product_uom_id.name,
                    ))
        return super().action_validate()

    def action_submit_for_approval(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Scrap orders can only be submitted in Draft status.'))
            if not rec.scrap_location_id:
                raise UserError(_('Please set a Scrap Location before submitting for approval.'))
            if rec.product_id and rec.location_id:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', '=', rec.location_id.id),
                ], limit=1)
                available_qty = quant.quantity if quant else 0.0
                if rec.scrap_qty > available_qty:
                    raise UserError(_(
                        'Cannot submit for approval: requested quantity (%s %s) '
                        'exceeds available stock (%s %s).'
                    ) % (
                        rec.scrap_qty,
                        rec.product_uom_id.name,
                        available_qty,
                        rec.product_uom_id.name,
                    ))
            rec.approval_deadline = fields.Datetime.now() + datetime.timedelta(hours=48)
            rec.state = 'waiting_approval'
            rec._notify_operations_managers()
            rec.sudo()._message_log(
                body=_(
                    'Submitted for approval by %s.<br/>Deadline: %s'
                ) % (
                    rec.sudo().create_uid.name,
                    rec.approval_deadline,
                )
            )

    def action_approve(self):
        self._check_is_operations_manager()
        for rec in self:
            if rec.state != 'waiting_approval':
                raise UserError(_('Approval is only possible in Waiting Approval status.'))
            rec.sudo().write({
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'approval_deadline': False,
            })
            rec.sudo().do_scrap()
            rec.sudo()._message_log(
                body=_('✅ Approved by %s') % self.env.user.name
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'waiting_approval'):
                raise UserError(_('Cancel is only possible in Draft or Waiting Approval status.'))
            rec.sudo().write({
                'state': 'cancel',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'approval_deadline': False,
            })
            rec.sudo()._message_log(
                body=_('❌ Cancelled by %s') % self.env.user.name
            )

    def action_reject(self):
        self._check_is_operations_manager()
        for rec in self:
            if rec.state != 'waiting_approval':
                raise UserError(_('Reject is only possible in Waiting Approval status.'))
        return {
            'name': _('Rejection Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrap.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_scrap_ids': self.ids,
                'is_rejection': True,
            },
        }

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state not in ('cancel', 'rejected'):
                raise UserError(_('Reset is only possible in Cancelled or Rejected status.'))
            rec.sudo().write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
                'cancellation_reason': False,
                'approval_deadline': False,
            })
            rec.sudo()._message_log(
                body=_('🔄 Reset to Draft by %s') % self.env.user.name
            )

    def _check_is_operations_manager(self):
        group = self.env.ref(
            'scrap_approval.group_scrap_operations_manager',
            raise_if_not_found=False
        )
        if not group or self.env.user not in group.user_ids:
            raise AccessError(_('Only the Operations Manager can approve or reject scrap orders.'))

    def _cron_notify_overdue_approvals(self):
        overdue = self.search([
            ('state', '=', 'waiting_approval'),
            ('approval_deadline', '<', fields.Datetime.now()),
        ])
        for rec in overdue:
            rec.sudo()._message_log(
                body=_(
                    '⚠️ Overdue for approval! Deadline was: %s'
                ) % rec.approval_deadline
            )

    def _notify_operations_managers(self):
        group = self.env.ref(
            'scrap_approval.group_scrap_operations_manager',
            raise_if_not_found=False
        )
        if not group:
            return
        partner_ids = group.user_ids.mapped('partner_id').ids
        for rec in self:
            rec.message_post(
                body=_(
                    'Scrap order <b>%s</b> submitted for approval.<br/>'
                    'Product: %s | Quantity: %s %s<br/>'
                    'Submitted by: %s<br/>'
                    '<b>Approval Deadline: %s</b>'
                ) % (
                    rec.name,
                    rec.product_id.display_name,
                    rec.scrap_qty,
                    rec.product_uom_id.name,
                    rec.sudo().create_uid.name,
                    rec.approval_deadline,
                ),
                partner_ids=partner_ids,
                subtype_xmlid='mail.mt_comment',
            )
