## Docker-Toolbox

This repository contains a set of useful services to manage and operate your local docker farm.


### Docker-Compose-Updater

Tracks Docker Images on Dockerhub and updates your local docker-compose files with new versions, see the [readme](docker-compose-updater/README.md) for further details.


### Ansible Playbook

This project includes an ansible playbook that sets up the services on the target machines. An example inventory can be found in `example_inventory.yml`. Copy the example inventory and adapt it to your needs:

```
cp example_inventory.yml inventory.yml
```

You can run the playbook with:

```
ansible-playbook -i inventory.yml ansible_playbook.yml
```

### License

This set of service scripts is published under the MIT License, see [LICENSE](LICENSE.txt) for further details.
