import importlib
import os
import threading
import time
from typing import List, Dict

import PySimpleGUI as sg
from termcolor import cprint

from baseplugin import ParamType, BasePlugin, HookCommandType, HookCommand
from functions import PluginError, ServerError, ValidationError
from smarthash import smarthash_version, SmartHash, MagicError


def collapsible(layout: List[List], key: str, visible: bool = True) -> sg.pin:
    return sg.pin(sg.Column(layout, key=key, visible=visible))


class Args(object):
    def __getitem__(self, key: str):
        return getattr(self, key)

    def __setitem__(self, key, val):
        setattr(self, key, val)

    def __contains__(self, item):
        return hasattr(self, item)


class SmartHashGui(SmartHash):

    MAIN_WIDTH = 80

    def __init__(self):
        self.load_config()

        if 'Smarthash GUI' not in self.config:
            self.config['Smarthash GUI'] = {'last path': ''}

        plugin_filenames = SmartHash.plugin_find()
        self.window = None
        self.plugins = {}
        self.curr_plugin = None
        self.folder_browsers = []
        self.curr_progress = 0
        self.is_hashing = False
        self.hooks = {}

        self.args = None

        for x in plugin_filenames:
            self.plugins[x] = importlib.import_module("Plugins." + x).SmarthashPlugin()
            self.plugins[x].set_config(self.config[self.plugins[x].title])

            if not hasattr(self.plugins[x], 'handle'):
                self.init_error("Could not import \"{0}\" plugin".format(x))
                continue

            if self.plugins[x].title not in self.config:
                self.config[self.plugins[x].title] = {}

            for hook in self.plugins[x].hooks:
                if hook.element_name not in self.hooks:
                    self.hooks[hook.element_name] = []
                self.hooks[hook.element_name].append(hook)

        self.early_return = False
        self.init_errors = []

        window_title = 'smarthash v{0}'.format(smarthash_version)
        window_initialization_text = "Loading plugins..." + " "*40

        initialization_text = collapsible([[
            sg.Text(window_initialization_text)
        ]], key='initialization_text')

        last_plugin_matches = [x for x in list(self.plugins.values())
                               if 'selected plugin' in self.config['Smarthash GUI'] and
                               x.title == self.config['Smarthash GUI']['selected plugin']]
        if last_plugin_matches:
            self.select_plugin(last_plugin_matches[0])
        else:
            self.select_plugin(list(self.plugins.values())[0])

        plugin_selection = [sg.Text("Select plugin: "),
                            sg.Combo([x.get_title() for x in self.plugins.values()],
                                     key='plugin_selection',
                                     default_value=self.curr_plugin.get_title(),
                                     enable_events=True,
                                     readonly=True,
                                     size=(30, 1))]

        initialization_error = collapsible([
            [sg.MLine(" " * 100, key='initialization_error_ml', visible=False, size=(None, 5), text_color='red')]
        ], key='initialization_error')

        progress_bar = collapsible([[
            sg.ProgressBar(1, orientation='h', size=(SmartHashGui.MAIN_WIDTH - 34, 20), key='progress_bar'),
            sg.Text("0.00%", size=(8, 1), key="progress_bar_percent")
        ]], key='progress_bar_wrapper', visible=False)

        hash_result = collapsible([[
            sg.Text(key='hash_result_txt', size=(60,1))
        ]], key='hash_result', visible=False)

        path_to_hash = self.config['Smarthash GUI']['last path'] \
            if self.config['Smarthash GUI']['last path'] else 'Select a folder to hash'

        main = collapsible([
            [sg.Text("Create a torrent from a folder")],
            [
                sg.Input(path_to_hash, key='path_to_hash', disabled=True, enable_events=True,
                         size=(SmartHashGui.MAIN_WIDTH, None)),
                sg.FolderBrowse()
            ],

            plugin_selection,

            self.generate_plugin_ui(),

            [progress_bar],
            [hash_result],
            [sg.Button("Create", key='create_button', disabled=True)],
        ], key='main', visible=False)

        self.layout = [
            [initialization_text],
            [initialization_error],
            [main]
        ]

        self.window = sg.Window(window_title, self.layout, icon='assets/icon.ico', finalize=True)

        # execute hooks
        for element, hooks in self.hooks.items():
            for hook in hooks:
                if hook.exec_on_init:
                    if type(self.window[element]) == sg.Combo:
                        value = self.window[element].DefaultValue
                    else:
                        value = self.window[element].DefaultText

                    self.exec_hook_commands_async(hook, value)

        # set the initial state of the create button
        self.update_create_button(self.window.read(0)[1])

        self.background_thread = threading.Thread(target=self.init)
        self.background_thread.start()

        self.run()

    def generate_plugin_ui(self) -> List[sg.Element]:

        plugin_ui = []

        for plugin in self.plugins.values():
            elements = []

            for param in plugin.parameters:
                default_value = param.default_value
                if plugin.title in self.config and param.name in self.config[plugin.title] and param.load_last_value:
                    default_value = self.config[plugin.title][param.name]

                    if param.param_type == ParamType.CHECKBOX and type(default_value) != bool:
                        default_value = default_value == "True"

                key = "{0}_{1}".format(plugin.get_title(), param.name)
                metadata = {'plugin': plugin.title, 'name': param.name, 'default_value': param.default_value}

                if param.param_type == ParamType.TEXT:
                    elements.append([
                        collapsible([[
                            sg.Text(param.label, size=(10, 1)),
                            sg.Input(default_value,
                                     key=key,
                                     enable_events=True,
                                     size=(SmartHashGui.MAIN_WIDTH - 12, None),
                                     metadata=metadata)
                        ]], visible=param.visible, key=key+'_wrapper')])

                elif param.param_type == ParamType.PATH:
                    elements.append([
                        collapsible([[
                            sg.Text(param.label, size=(10, 1)),
                            sg.Input(default_value,
                                     key=key,
                                     enable_events=True,
                                     readonly=True,
                                     metadata=metadata),
                            sg.FolderBrowse()
                        ]], visible=param.visible, key=key+'_wrapper')])
                    self.folder_browsers.append(key)

                elif param.param_type == ParamType.SELECT:
                    elements.append([
                        collapsible([[
                            sg.Text(param.label, size=(10, 1)),
                            sg.Combo(param.options,
                                     key=key,
                                     default_value=default_value,
                                     enable_events=True,
                                     readonly=True,
                                     size=(30, 1),
                                     metadata=metadata)
                        ]], visible=param.visible, key=key+'_wrapper')])

                elif param.param_type == ParamType.CHECKBOX:
                    elements.append([
                        collapsible([[
                            sg.Checkbox(param.label,
                                        key=key,
                                        default=default_value,
                                        enable_events=True,
                                        metadata=metadata)
                        ]], visible=param.visible, key=key+'_wrapper')])

                elif param.param_type == ParamType.RADIO:
                    buttons = []
                    for option in param.options:
                        buttons.append(
                            sg.Radio(option,
                                     key,
                                     default=(option == param.default_value),
                                     enable_events=True,
                                     key=key+'_'+option)
                        )
                    elements.append([
                        collapsible([buttons], visible=param.visible, key=key+'_wrapper')])

            visible = plugin.get_title() == self.curr_plugin.get_title()
            plugin_ui.append(
                collapsible(elements, visible=visible, key=plugin.get_title())
            )

        return plugin_ui

    def select_plugin(self, plugin: BasePlugin) -> None:

        for _, curr_plugin in self.plugins.items():
            visible = curr_plugin == plugin
            if self.window:
                self.window[curr_plugin.get_title()].update(visible=visible)
            if visible:
                self.curr_plugin = plugin
                self.config['Smarthash GUI']['selected plugin'] = curr_plugin.title

    def init(self):

        for plugin in self.plugins.values():
            self.plugin_update(plugin)

        if self.init_errors:
            pass

        self.window['initialization_text'].update(visible=False)
        self.window['main'].update(visible=True)

    def run(self):
        while True:  # The Event Loop
            event, values = self.window.read()

            if event == sg.WIN_CLOSED or event == 'Exit':
                self.terminate()
                break

            # append a path separator to inputs
            if event in self.folder_browsers \
                    and len(values[event]) and values[event][-1] != '/' and os.path.isdir(values[event]):
                values[event] += '/'
                self.window[event].update(values[event])

            if event == "create_button":

                self.args = Args()
                self.args['path'] = values['path_to_hash']

                for param in self.curr_plugin.parameters:
                    if param.param_type == ParamType.RADIO:
                        for option in param.options:
                            if values["{0}_{1}_{2}".format(self.curr_plugin.get_title(), param.name, option)]:
                                setattr(self.args, param.name, option)
                    else:
                        key = "{0}_{1}".format(self.curr_plugin.get_title(), param.name)
                        setattr(self.args, param.name, values[key])

                self.background_thread = threading.Thread(target=self.hash_func,
                                                          kwargs={'path': values['path_to_hash']})

                self.window['create_button'].update('Hashing...', disabled=True)
                self.window['progress_bar'].update(0)
                self.window['progress_bar_percent'].update("{:.1f}%".format(0))
                self.window['progress_bar_wrapper'].update(visible=True)

                self.background_thread.start()

            if event == "plugin_selection":
                for plugin in self.plugins.values():
                    if plugin.get_title() == values['plugin_selection']:
                        self.select_plugin(plugin)
                        self.config['Smarthash GUI']['selected plugin'] = plugin.title

            if event == "path_to_hash":
                self.config['Smarthash GUI']['last path'] = values[event]

            # match the event with inputs to the current plugin, save to global config
            if self.window[event].metadata and 'plugin' in self.window[event].metadata:
                element_metadata = self.window[event].metadata
                self.config[element_metadata['plugin']][element_metadata['name']] = str(values[event])

            # execute hooks
            if event in self.hooks:
                for hook in self.hooks[event]:
                    threading.Thread(target=self.exec_hook_commands_async, args=(hook, values[event])).start()

            self.update_create_button(values)

            print(event)

        self.window.close()

    def exec_hook_commands_async(self, hook, value):
        commands = hook.function(value)
        for command in commands:
            self.exec_hook_command(command)

    def exec_hook_command(self, command: HookCommand) -> None:
        if command.command_type == HookCommandType.UPDATE:
            self.window[command.element_name].update(command.value)
        elif command.command_type == HookCommandType.VISIBLE:
            self.window[command.element_name].update(visible=command.value)
        elif command.command_type == HookCommandType.OPTIONS:
            old_value = self.window[command.element_name].get()
            new_value = old_value if old_value in self.window[command.element_name].Values \
                else self.window[command.element_name].metadata['default_value']
            self.window[command.element_name].update(new_value, values=command.value)

    def update_create_button(self, values: Dict) -> None:
        # reevaluate the create button's disabled status for all changes
        create_disabled = False
        if not os.path.isdir(values['path_to_hash']):
            create_disabled = True

        parameters = {x.name: x for x in self.curr_plugin.parameters if x.required}

        for param in parameters.values():

            # checkbox param types always have a value
            if param.param_type == ParamType.CHECKBOX:
                continue

            elif param.param_type == ParamType.RADIO:
                selected = False
                for option in param.options:
                    if values["{0}_{1}_{2}".format(self.curr_plugin.get_title(), param.name, option)]:
                        selected = True
                if not selected:
                    create_disabled = True

            else:
                value = values["{0}_{1}".format(self.curr_plugin.get_title(), param.name)]
                if not value or value == param.default_value:
                    create_disabled = True

        if self.is_hashing:
            create_disabled = True

        self.window['create_button'].update(disabled=create_disabled)

    def hash_func(self, path):
        self.process_folder_wrapper(path)

    def process_folder_wrapper(self, path: str):
        self.is_hashing = True
        self.window['hash_result'].update(visible=False)

        try:
            self.process_folder(path, self.curr_plugin)
            self.window['hash_result_txt'].update('Success!', text_color='green3')

        except ValidationError as e:
            if e.errors and len(e.errors[0]) > 400:
                e.errors[0] = "<error message is too long to display>"
            self.window['hash_result_txt'].update(e.errors[0], text_color='red2')

        except (MagicError, PluginError) as e:
            self.window['hash_result_txt'].update(e.error, text_color='red2')

        except ServerError as e:
            self.window['hash_result_txt'].update(e.error, text_color='red2')
            time.sleep(1)
            self.process_folder_wrapper(path)

        finally:
            self.window['progress_bar_wrapper'].update(visible=False)
            self.window['hash_result'].update(visible=True)
            self.window['create_button'].update('Create', disabled=False)
            self.is_hashing = False

    def init_error(self, msg: str):
        if self.init_errors and self.init_errors[-1][0] == msg:
            self.init_errors[-1][1] += 1

        else:
            self.init_errors.append([msg, 1])

        combined_msg = "\n".join([self.__flatten_error(x) for x in self.init_errors])
        self.window['initialization_error_ml'].update(visible=True, value=combined_msg)
        cprint(msg, 'red')

    def hash_progress_callback(self, amount):
        factor = 0.4 if 'video-screenshots' in self.curr_plugin.options else 0.5
        self.curr_progress = amount * factor
        self.window['progress_bar'].update(self.curr_progress)
        self.window['progress_bar_percent'].update("{:.1f}%".format(self.curr_progress*100))

    def pricker_progress_callback(self, num_bytes) -> None:
        factor = 0.4 if 'video-screenshots' in self.curr_plugin.options else 0.5
        self.curr_progress = factor + (num_bytes/self.total_media_size)* factor
        self.window['progress_bar'].update(self.curr_progress)
        self.window['progress_bar_percent'].update("{:.1f}%".format(self.curr_progress*100))

    def image_extaction_progress_callback(self, x: int, total_images: int) -> None:
        self.curr_progress = 0.8 + (x / total_images) * 0.2
        self.window['progress_bar'].update(self.curr_progress)
        self.window['progress_bar_percent'].update("{:.1f}%".format(self.curr_progress*100))

    @staticmethod
    def __flatten_error(err):
        if err[1] == 1:
            return err[0]
        return "{0} [{1}]".format(err[0], err[1])

    def clear_error(self):
        self.window['initialization_error'].update(visible=False)


if __name__ == "__main__":
    smarthash = SmartHashGui()
