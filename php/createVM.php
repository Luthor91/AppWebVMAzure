<?php

	/**
	 *  Fichier de création de la VM sur le Cloud Azure
	 * 	Permet de : 
	 * 		Créer une VM
	 * 		Connaitre la commande à utiliser pourla connexion
	 * 		Connaitre des données sur la VM créé
	 * 		Gérer le cas où la VM est une Windows ou Linux
	 * 		Gérer le cas où la machine physique est une Windows ou Linux
	 * 		Exécute le scripts scripts/createVM.py 
	 * 
	 * 
	 * 		Prévu : 
	 * 			Affichage du nom de la VM
	 * 			Affichage du groupe de ressource de la VM
	 * 			
	 */

	/**
	 *  Définition des données globales et de configuration
	 * 
	 */
	include_once("function.php");
	if (session_status() == PHP_SESSION_NONE) {
		session_start();
	}
	if(isset($_SESSION['sudo'])){
		$sudo = $_SESSION['sudo'];
	}
	
	$dataVirtualMachine = getConfigFile('config');
	$os = getOS();

	
?>

<html>
	<head>
		<title>createVM</title>
	</head>
	<body>	
		<legend>Creation de la VM</legend>
		<BR>


		<?php
			/**
			 *  Définition des divers chemins utilisés
			 * 
			 */
			$pathToMain =  __DIR__ . DIRECTORY_SEPARATOR . '..';
			$pathToVenv = $pathToMain . DIRECTORY_SEPARATOR . "scripts". DIRECTORY_SEPARATOR . "vmazureenv";
			$pathToRequire = $pathToMain . DIRECTORY_SEPARATOR . "resources". DIRECTORY_SEPARATOR . "requirements.txt";
			/**
			 * Si le script scripts/createVM.py a été exécuté 
			 * ou si le formulaire d'envoie de donnée depuis php/defaultVM ou php/selectVM a été validé
			 */

			if(isset($_POST['form'])) {
				foreach ($_POST as $key => $value) {
					if($key == 'form') {
						continue;
					}
					if($key == 'name_virtual_machine' && empty($value)){
						$value = 'vmname';
					}
					updateConfigFile('config', array($key => $value));
					$dataVirtualMachine[$key] = $value;
				}

			}
			echo"<p>
			Caracteristique de la machine choisi :<br>";
			foreach ($dataVirtualMachine as $key => $value) {
				echo "$key \t=>\t $value<br>";
			}
			if(!str_starts_with($dataVirtualMachine['operating_system'], 'w')){
				/**
				 * Si la machine virtuelle sélectionné est une Linux
				 * 
				 */
				echo "Lancez un terminal et utilisez la commande suivante :<br>
				ssh $dataVirtualMachine[username]@$dataVirtualMachine[ip_address] -p 22<br></p>";
			} else{
				/**
				* Si la machine virtuelle sélectionné est une Windows
				* 
				*/
				echo "Lancez un terminal et utilisez la commande suivante :<br>
				rdesktop [ip_address] -u $dataVirtualMachine[username] -p $dataVirtualMachine[password]</p>";
			}
			echo "<p>
					<br><br>Si l'adresse IP ne s'est pas correctement affichee,<br> 
					regardez dans le terminal qui a ete execute par l'application <br>
					Sinon regardez sur le Portail Azure<br>
					Attendez qu'un terminal soit ouvert par l'application pour continuer<br>
					Il est conseille d'attendre que les autres scripts de creation de VM aient fini<br>
					<br>
					Temps estime : 7 minutes.<br><br>
					</p>";


			/**
			* Si le bouton d'exécution du script scripts/createVM.py a été clické
			* 
			*/

			if(isset($_POST['execute'])) {
				$python_versions = array("python3", "python");
				if($os == 'Windows') {
					/*****
					 * 	Sur Windows
					 */
					$command = "$pathToVenv/Scripts/python $pathToMain/scripts/createVM.py";

				} else {
					/*****
					 * 	Sur Linux
					 */
					$command = 'sudo -S ' . $pathToVenv . '/bin/python3 ' . $pathToMain . '/scripts/createVM.py <<< "'. $sudo . '"';
					 
				}

				/**
				 *  Permet d'exécuter le script sans bloquer le site Web
				 * 
				 */
				execInBackground($command);
					
			} else {
				/**
				 *  Si le bouton d'exécution n'a pas été pressé alors 
				 *  Permet de limiter de manière rudimentaire le lancement de machine virtuelle
				 * 
				 */

				echo "<form action=createVM.php method=post>
						<input type=submit name=execute value=Executer />	
					</form>";
			}
			
		?>

	</body>
	<BR>
	<a href="config.php">page de modification des valeurs par defaut</a>
	<BR>		
	<a href="login.php">retour page de connexion</a>
	<BR>
	<BR>
</html>