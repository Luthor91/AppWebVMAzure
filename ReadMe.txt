###########################
#  Fonctionnement
###########################

appWebAzurePython est le nom du répertoire dans lequel vous avez trouvé ce fichier.

Cette application fonctionne sur Windows et Linux avec une interface graphique fonctionnelle
Elle permet de choisir une VM sur le cloud Azure
Les VM possible sont : 
Ubuntu sans interface graphique
Debian sans interface graphique
Windows 10
Windows Server avec interface graphique

Le timer avant destruction de la VM est de 10 minutes et est modifiable, il se déclenche au moment de la création
La région où se situera la VM est modifiable, les régions sont situés aux USA, en France et en Europe
Le nom d'utilisateur et le mot de passe sont générés aléatoirement

Pour le moment seuls 3 comptes sont existants
un compte ayant aucun droit :
	username => crook
	password => crook
un compte ayant le droit à une seule VM pré-configuré :
	username => hitman
	password => hitman
un compte ayant le droit de créer la VM qu'il veux :
	username => boss
	password => boss

Autant de machine que vous voulez peuvent être lancé à la fois.
Le comportement normal n'est pas assuré si une autre machine virtuelle porte le nom d'une machine virtuelle déjà existante
Le temps d'installation des package est de 1 à 3 minutes.
Le temps de création de la VM dépend entièrement de la connexion internet et du site d'Azure
temps estimé entre 7 minutes et 15 minutes.
Le temps de suppression de la VM est estimé à 3 minutes.

###########################
#  Pré-requis 
###########################

Cette application à besoin de quelques pré-requis pour fonctionner :
	-Python, PHP, Pip
	-les commandes rdesktop, ssh et xterm existantes sur la machine Linux
	-Une connexion internet
	-Un abonnement Azure actif

###########################
#  Guide d'installation 
###########################

Une fois le dossier compressé fournis et décompressé, exécutez php/index.php	

Python devrait être installé de base sur toutes les machines Linux.
Pour installer php :
	-Ouvrez un terminal
	-Entrez =>
		sudo apt-get update
		sudo apt-get install apache2
		sudo apt-get install php libapache2-mod-php
		sudo apt-get install php
		/etc/init.d/apache2 restart

Pour exécuter l'application :
	-Aller à l'adresse suivante dans un navigateur Web =>
		http://localhost/appWebAzurePython/php/index.php

Pour installer pip :
	-Ouvrez un terminal
	-Entrez =>
		sudo apt install python3-pip
	-Validez

Pour installer rdesktop :
	-Ouvrez un terminal
	-Entrez =>
		sudo apt install rdesktop
	-Validez

Pour installer xterm :
	-Ouvrez un terminal
	-Entrez =>
		sudo apt install xterm
	-Validez

Pour le bon fonctionnement de l'application :
	Un problème avec l'application nécessite de suivre ces étapes : 
		-Aller à cette adresse dans un navigateur Web =>
			http://localhost/appWebAzurePython/php/index.php
		-Cliquer sur le bouton "Installation"
		-Attendre que la redirection vers login.php soit effectuée
		-Ouvrir un terminal 
		-Entrez =>
			sudo chmod -R a+rwx /var/www/html/appWebAzurePython/
	-Ouvrez un terminal
	-Entrez =>	
		sudo cp -R /chemin/vers/le/repertoire/appWebAzurePython /var/www/html/
		Pour la commande ci-dessous la version de python à renseigner dans la commande 
			dépend du message d'erreur reçu lors du lancement de index.php
		sudo apt install python3.10-venv


###########################
#  Contenue
###########################

L'application contient 4 répertoires, data, php, resources et scripts

Le répertoire data contient deux azure.json et config.json
	azure.json contient les données de connexion pour le compte Azure
	config.json contient les données de configuration pour la VM

Le répertoire php contient les pages php de l'application, index.php permet de démarrer l'application

Le répertoire resources contient les fichiers log.txt et requirements.txt
	log.txt contient les logs de l'application
	requirements.txt contient les packages a installer par Python

Le répertoire scripts contient le script Python à exécuter par l'application et l'environnement virtuel utilisé


###########################
#  En cas de problèmes
###########################

Si il y a des lignes de codes d'affichés au lieu d'être exécutez essayez ces 
	-sudo chmod 777 /var/www/html/appWebAzurePython/php/*.php
	-sudo apt install dos2unix
	-sudo dos2unix /var/www/html/appWebAzurePython/php/*.php
Elles permettent de donner tout droits et de convertir les fichiers php en format mieux lisible par Unix


#################################################################################
Si il y a des problèmes de fonctionnement de l'application 
#################################################################################

Si problème de PHP : 
	-Ouvrez un terminal
	-Entrez =>
		-sudo apt install libapache2-mod-php libapache2-mod-php8.1
		-pip install -r chemin/vers/application/resources/requirements.txt
		Sur Debian : 
			sudo nano /etc/apache2/apache2.conf
			Rajouter la ligner suivante :
				DirectoryIndex index.html index.cgi index.pl index.php index.xhtml index.htm
		Sur Ubuntu : 
			sudo nano /etc/apache2/apache2.conf
			Rajouter la ligne suivante :
			Include /etc/php/8.1/apache2/php.ini
		/etc/init.d/apache2 restart


Si problème de package Python : 
	-Ouvrez un terminal
	-Entrez =>
		sudo chmod -R a+rwx /var/www/html/appWebAzurePython/
		sudo python3 -m venv /var/www/html/appWebAzurePython/scripts/vmazureenv vmazureenv
		sudo chmod -R a+rwx /var/www/html/appWebAzurePython/scripts/vmazureenv
		source /var/www/html/appWebAzurePython/scripts/vmazureenv/bin/activate
		sudo pip install -r /var/www/html/appWebAzurePython/resources/requirements.txt

Si il y a aucune VM de créée :
	-Ouvrez un terminal
	-Entrez =>
		/var/www/html/appWebAzurePython/scripts/vmazureenv/bin/python3 /var/www/html/appWebAzurePython/scripts/vmazureenv/bin/pip install -r /var/www/html/appWebAzurePython/resources/requirements.txt
		sudo pip install -r /chemin/vers/resources/requirements.txt
	Cette ligne de commande permet d'installer les packages qui n'ont pas réussi a être installé apr l'application

Si il y a une erreur de temps d'exécution trop long :
	modifiez la ligne 19 de php/index.php à une valeur supérieur (valeur en secondes)
		set_time_limit(180);
	

###########################
#  Problèmes connus
###########################

Il y a 2 environnements virtuel Python de créé, 
un dans le répertoire php et un dans scripts, seul celui dans scripts est utilisé

Il risque d'y avoir des problèmes d'installation si vous n'avez pas la capacité d'utiliser des commandes sudo

Les mots de passes et nom d'utilisateur ne sont pas parfaitement aléatoires
