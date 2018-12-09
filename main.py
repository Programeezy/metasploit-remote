import json
from collections import namedtuple

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager


class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """

    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        print(json.dumps({host.name: result._result}, indent=4))


def main():
    Options = namedtuple('Options', [
        'connection',
        'module_path',
        'forks',
        'become',
        'become_method',
        'become_user',
        'check',
        'diff',
        'verbosity',
        'private_key_file',
        'remote_user',
    ])

    options = Options(connection='ssh',
                      module_path=[],
                      forks=10,
                      become=True,
                      become_method='sudo',
                      become_user='root',
                      check=False,
                      diff=False,
                      verbosity=None,
                      private_key_file='~/.ssh/metasploit-key.pem',
                      remote_user='ubuntu'
                      )

    loader = DataLoader()  # Takes care of finding and reading yaml, json and ini files
    passwords = dict(vault_pass='secret')

    results_callback = ResultCallback()

    # create inventory, use path to host config file as source or hosts in a comma separated string
    inventory = InventoryManager(loader=loader, sources='18.194.205.225,')

    variable_manager = VariableManager(loader=loader, inventory=inventory)

    variable_manager.extra_vars = {'ansible_python_interpreter': '/usr/bin/python3'}

    play_source = dict(
        name="Ansible Play",
        hosts='18.194.205.225',
        gather_facts='no',
        tasks=[
            dict(action=dict(module='shell', args='ls'), register='shell_out'),
            dict(action=dict(module='debug', args=dict(msg='{{shell_out.stdout}}'))),

            dict(action=dict(module='apt_repository', args=dict(
                repo='deb http://ppa.launchpad.net/backbox/four/ubuntu trusty main',
                codename='trusty',
                validate_certs=False
            ))),
            dict(action=dict(module='apt_repository', args=dict(
                repo='deb-src http://ppa.launchpad.net/backbox/four/ubuntu trusty main',
                codename='trusty',
                validate_certs=False
            ))),
            dict(action=dict(module='apt', update_cache=True, args=dict(name='{{packages}}')), vars=dict(packages=[
                'apt-transport-https',
                'ca-certificates',
                'curl',
                'software-properties-common',
                'shellter'
            ])),
            dict(action=dict(module='apt_key', args=dict(
                url='https://download.docker.com/linux/ubuntu/gpg'
            ))),
            dict(action=dict(module='apt_repository', args=dict(
                repo='deb [arch=amd64] https://download.docker.com/linux/ubuntu/ bionic stable',
                codename='bionic'
            ))),
            dict(action=dict(module='apt', args=dict(name='{{packages}}')), vars=dict(packages=[
                'docker-ce',
                'python3-pip'
            ])),
            dict(action=dict(module='pip', args=dict(name='docker')))
        ]
    )

    # Create play object, playbook objects use .load instead of init or new methods,
    # this will also automatically create the task objects from the info provided in play_source
    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    tqm = None
    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=options,
            passwords=passwords
            # Use our custom callback instead of the ``default`` callback plugin, which prints to stdout
        )
        result = tqm.run(play)  # most interesting data for a play is actually sent to the callback's methods
    finally:
        # we always need to cleanup child procs and the structres we use to communicate with them
        if tqm is not None:
            tqm.cleanup()


if __name__ == '__main__':
    main()
