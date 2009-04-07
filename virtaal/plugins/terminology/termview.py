#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import logging

from virtaal.views import BaseView
from virtaal.views.placeablesguiinfo import StringElemGUI
from virtaal.views.widgets.selectdialog import SelectDialog


class TerminologyGUIInfo(StringElemGUI):
    """
    GUI info object for terminology placeables. It creates a combo box to
    choose the selected match from.
    """
    # MEMBERS #
    bg = '#eeffee'
    fg = '#006600'

    def __init__(self, elem, textbox, **kwargs):
        assert elem.__class__.__name__ == 'TerminologyPlaceable'
        super(TerminologyGUIInfo, self).__init__(elem, textbox, **kwargs)


    # METHODS #
    def create_widget(self):
        if len(self.elem.translations) > 1:
            return TerminologyCombo(self.elem)
        return None


class TerminologyCombo(gtk.ComboBox):
    """
    A combo box containing translation matches.
    """

    # INITIALIZERS #
    def __init__(self, elem):
        super(TerminologyCombo, self).__init__()
        self.anchor = None
        self.elem = elem
        self.insert_iter = None
        self.selected_string = None
        # FIXME: The following height value should be calculated from the target font.
        self.set_size_request(-1, 20)
        self.__init_combo()
        self.menu = self.menu_get_for_attach_widget()[0]
        self.menu.connect('selection-done', self._on_selection_done)

    def __init_combo(self):
        self._model = gtk.ListStore(str)
        for trans in self.elem.translations:
            self._model.append([trans])

        self.set_model(self._model)
        self._renderer = gtk.CellRendererText()
        self.pack_start(self._renderer)
        self.add_attribute(self._renderer, 'text', 0)


    # METHODS #
    def inserted(self, insert_iter, anchor):
        self.anchor = anchor
        self.insert_iter = insert_iter
        self.grab_focus()
        self.popup()

    def insert_selected(self):
        iter = self.get_active_iter()
        if iter:
            self.selected_string = self._model.get_value(iter, 0)

        if self.parent:
            self.parent.grab_focus()

        buffer = self.parent.get_buffer()
        if self.insert_iter:
            iternext = buffer.get_iter_at_offset(self.insert_iter.get_offset() + 1)
            if iternext:
                # FIXME: Not sure if the following is the best way to remove the combo box
                # from the text view.
                buffer.backspace(iternext, False, True)

        if self.selected_string:
            buffer.insert_at_cursor(self.selected_string)


    # EVENT HANDLERS #
    def _on_selection_done(self, menushell):
        self.insert_selected()


class TerminologyView(BaseView):
    """
    Does general GUI setup for the terminology plug-in.
    """

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        self._signal_ids = []
        self._setup_menus()

    def _setup_menus(self):
        mainview = self.controller.main_controller.view
        self.mnu_term = mainview.find_menu(_('_Terminology'))
        if self.mnu_term is None:
            self.mnu_term = mainview.append_menu(_('_Terminology'))
        self.menu = self.mnu_term.get_submenu()

        self.mnu_backends, _menu = mainview.find_menu_item(_('Select back-ends...'), self.mnu_term)
        if not self.mnu_backends:
            self.mnu_backends = mainview.append_menu_item(_('Select back-ends...'), self.mnu_term)
        self._signal_ids.append((
            self.mnu_backends,
            self.mnu_backends.connect('activate', self._on_select_backends)
        ))


    # METHODS #
    def destroy(self):
        for gobj, signal_id in self._signal_ids:
            gobj.disconnect(signal_id)

        menubar = self.controller.main_controller.view.menubar
        menubar.remove(self.mnu_term)


    # EVENT HANDLERS #
    def _on_select_backends(self, menuitem):
        selectdlg = SelectDialog(
            title='Select TM back-ends',
            message='Please select the TM back-ends you would like to have enabled.'
        )

        items = []
        plugin_controller = self.controller.plugin_controller
        disabled_plugins = plugin_controller.get_disabled_plugins()
        for plugin_name in plugin_controller._find_plugin_names():
            if plugin_name in disabled_plugins:
                continue
            item = {'name': plugin_name}
            if plugin_name in plugin_controller.plugins:
                plugin = plugin_controller.plugins[plugin_name]
                item.update({
                    'desc': getattr(plugin, plugin_controller.PLUGIN_NAME_ATTRIB),
                    'enabled': True
                })
            else:
                item['enabled'] = False
            items.append(item)

        if selectdlg.run(items=items) == gtk.RESPONSE_OK:
            for item in selectdlg.sview.get_all_items():
                if item['enabled']:
                    plugin_controller.enable_plugin(item['name'])
                else:
                    plugin_controller.disable_plugin(item['name'])
