# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014-2017 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Functions that return miscellaneous completion models."""

from PyQt5.QtCore import Qt

from qutebrowser.config import config, configdata
from qutebrowser.utils import objreg, log, qtutils
from qutebrowser.commands import cmdutils
from qutebrowser.completion.models import base


def command():
    """A CompletionModel filled with non-hidden commands and descriptions."""
    model = base.CompletionModel(column_widths=(20, 60, 20))
    cmdlist = _get_cmd_completions(include_aliases=True, include_hidden=False)
    cat = model.new_category("Commands")
    for (name, desc, misc) in cmdlist:
        model.new_item(cat, name, desc, misc)
    return model


def helptopic():
    """A CompletionModel filled with help topics."""
    model = base.CompletionModel()

    cmdlist = _get_cmd_completions(include_aliases=False, include_hidden=True,
                                   prefix=':')
    cat = model.new_category("Commands")
    for (name, desc, misc) in cmdlist:
        model.new_item(cat, name, desc, misc)

    cat = model.new_category("Settings")
    for sectname, sectdata in configdata.DATA.items():
        for optname in sectdata:
            try:
                desc = sectdata.descriptions[optname]
            except (KeyError, AttributeError):
                # Some stuff (especially ValueList items) don't have a
                # description.
                desc = ""
            else:
                desc = desc.splitlines()[0]
            name = '{}->{}'.format(sectname, optname)
            model.new_item(cat, name, desc)
    return model


def quickmark():
    """A CompletionModel filled with all quickmarks."""
    model = base.CompletionModel()
    cat = model.new_category("Quickmarks")
    quickmarks = objreg.get('quickmark-manager').marks.items()
    for qm_name, qm_url in quickmarks:
        model.new_item(cat, qm_name, qm_url)
    return model


def bookmark():
    """A CompletionModel filled with all bookmarks."""
    model = base.CompletionModel()
    cat = model.new_category("Bookmarks")
    bookmarks = objreg.get('bookmark-manager').marks.items()
    for bm_url, bm_title in bookmarks:
        model.new_item(cat, bm_url, bm_title)
    return model


def session():
    """A CompletionModel filled with session names."""
    model = base.CompletionModel()
    cat = model.new_category("Sessions")
    try:
        for name in objreg.get('session-manager').list_sessions():
            if not name.startswith('_'):
                model.new_item(cat, name)
    except OSError:
        log.completion.exception("Failed to list sessions!")
    return model


def buffer():
    """A model to complete on open tabs across all windows.

    Used for switching the buffer command.
    """
    idx_column = 0
    url_column = 1
    text_column = 2

    def delete_buffer(completion):
        """Close the selected tab."""
        index = completion.currentIndex()
        qtutils.ensure_valid(index)
        category = index.parent()
        qtutils.ensure_valid(category)
        index = category.child(index.row(), idx_column)
        win_id, tab_index = index.data().split('/')
        tabbed_browser = objreg.get('tabbed-browser', scope='window',
                                    window=int(win_id))
        tabbed_browser.on_tab_close_requested(int(tab_index) - 1)

    model = base.CompletionModel(
        column_widths=(6, 40, 54),
        dumb_sort=Qt.DescendingOrder,
        delete_cur_item=delete_buffer,
        columns_to_filter=[idx_column, url_column, text_column])

    for win_id in objreg.window_registry:
        tabbed_browser = objreg.get('tabbed-browser', scope='window',
                                    window=win_id)
        if tabbed_browser.shutting_down:
            continue
        c = model.new_category("{}".format(win_id))
        for idx in range(tabbed_browser.count()):
            tab = tabbed_browser.widget(idx)
            model.new_item(c, "{}/{}".format(win_id, idx + 1),
                           tab.url().toDisplayString(),
                           tabbed_browser.page_title(idx))
    return model


def bind(_):
    """A CompletionModel filled with all bindable commands and descriptions.

    Args:
        _: the key being bound.
    """
    # TODO: offer a 'Current binding' completion based on the key.
    model = base.CompletionModel(column_widths=(20, 60, 20))
    cmdlist = _get_cmd_completions(include_hidden=True, include_aliases=True)
    cat = model.new_category("Commands")
    for (name, desc, misc) in cmdlist:
        model.new_item(cat, name, desc, misc)
    return model


def _get_cmd_completions(include_hidden, include_aliases, prefix=''):
    """Get a list of completions info for commands, sorted by name.

    Args:
        include_hidden: True to include commands annotated with hide=True.
        include_aliases: True to include command aliases.
        prefix: String to append to the command name.

    Return: A list of tuples of form (name, description, bindings).
    """
    assert cmdutils.cmd_dict
    cmdlist = []
    cmd_to_keys = objreg.get('key-config').get_reverse_bindings_for('normal')
    for obj in set(cmdutils.cmd_dict.values()):
        hide_debug = obj.debug and not objreg.get('args').debug
        hide_hidden = obj.hide and not include_hidden
        if not (hide_debug or hide_hidden or obj.deprecated):
            bindings = ', '.join(cmd_to_keys.get(obj.name, []))
            cmdlist.append((prefix + obj.name, obj.desc, bindings))

    if include_aliases:
        for name, cmd in config.section('aliases').items():
            bindings = ', '.join(cmd_to_keys.get(name, []))
            cmdlist.append((name, "Alias for '{}'".format(cmd), bindings))

    return cmdlist
