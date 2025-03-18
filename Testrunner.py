import ansible_runner

r = ansible_runner.run(
    inventory = 'inventory',
    module = 'ping',
    host_pattern='esxi',
    extravars={
        'ansible_user': 'root',
        'ansible_password': 'password'
    }
)

if r.status == 'successful':
    print('The playbook was run successfully')
else:
    print('The playbook failed')