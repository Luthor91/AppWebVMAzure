<?php

	/**
	 *  Fichier de configuration pour la connexion à Azure et les paramètres de la VM
	 * 	Permet de modifier : 
	 * 		Temps du timer de destruction
	 * 		OS de la VM par défaut
	 * 		Région de la VM par défaut
	 * 		Abonnement, Secret Id, Tenant Id, Client Id
	 * 
	 * 
	 * 		Prévu : 
	 * 			Modification nom de la VM
	 * 			Modification groupe de ressource de la VM
	 * 			Modification version de Python à utiliser par défaut
	 * 			Modification version de Pip à utiliser par défaut
	 * 			Modification de la structure des fichiers configuration
	 */

	/**
	 *  Définition des données globales et de configuration
	 * 
	 */
	if (session_status() == PHP_SESSION_NONE) {
		session_start();
	}
	include_once("function.php");
	$jsonConfig = getConfigFile('config');
	$jsonAzure = getConfigFile('azure');
?>

<html>
	<head>
		<title>Configuration</title>
	</head>
	<body>	
		<tr>
		<p>
			Parametres actuels :
			<BR>
			<BLOCKQUOTE>
			 <?
				foreach ($jsonConfig as $key => $value) {
					echo "$key => $value<br>";
				}
			?> 
			</BLOCKQUOTE>
		</p>
		<p> 
			Azure Connexion actuels :
			<BR>
			<BLOCKQUOTE>
			<?
				foreach ($jsonAzure as $key => $value) {
					if($value == 'null') {
						$value = '';
					}
					echo "$key => $value<br>";
				}
			?>
			</BLOCKQUOTE>
		</p>
		</tr>
		<form action="config.php" method="post">
			<legend>Configuration</legend>
			<p> 
				Duree du Timer en minute
				<BR>
				<input type="text" name="TimerDuration" value="10"/>
			</p>
			<p> 
				Debut du Timer de destruction (WIP)
				<BR>
				<select name="startTimer" id="timerStart-select">
					<option value="conn">Dès la creation</option>
					<option value="disc">Dès la première deconnexion</option>
				</select>
			</p>
			<p> 
				Selection de l'OS par defaut
				<BR>
				<select name="defaultOS" id="defaultOS-select">
					<option value="debian">debian</option>
					<option value="debianDesktop">Debian Desktop</option>
					<option value="ubuntu">Ubuntu Server</option>
					<option value="ubuntuDesktop">Ubuntu Desktop</option>
					<option value="windowsServer">Windows Server</option>
					<option value="windowsDesktop">Windows 10</option>
				</select>
			</p>
			<p> 
				Selection de la region par defaut
				<BR>
				<select name="defaultRegion" id="defaultRegion-select">
					<option value="northeurope">Europe du Nord</option>
					<option value="westeurope">Europe de l'Ouest</option>
					<option value="uksouth">Royaume-Uni Sud</option>
					<option value="francecentral">France Centrale</option>
					<option value="westcentralus">Allemagne Ouest Central</option>
					<option value="eastus">Est des Etats-Unis</option>
					<option value="centralus">Centre des Etats-Unis</option>
					<option value="westus">Ouest des Etats-Unis</option>
					<option value="canadacentral">Canada Central</option>
					<option value="canadaeast">Canada Est</option>
					<option value="brazilsouth">Bresil Sud</option>
				</select>
			</p>
			<legend>Connexion Azure</legend>
			<p> 
				TENANT ID :
				<input type="text" name="TENANT">
				<BR>
				CLIENT : 
				<input type="text" name="CLIENT">
				<BR>
				ID CLIENT SECRET : 
				<input type="text" name="SECRET">
				<BR>
				SUBSCRIPTION ID : 
				<input type="text" name="SUBSCRIPTION">
				<BR>
			</p>
			<input type="submit" name="form" value="Envoyer" />	
		</form>
		<BR><BR>
		<a href="config.php">page de modification des valeurs par defaut</a>
		<BR>		
		<a href="login.php">retour page de connexion</a>
		<BR>		
	</body>
</html>

<?php
	if(isset($_POST['form'])) {	

		/**
		 * 	Attribut les valeurs de configuration et paramètres dans les bons fichiers
		 * 
		 * 
		 */

		/**
		 *  Code en chantier ci-dessous
		 * 		associer les valeurs de connexion a Azure à $_POST['azure_connexion']
		 * 		associer les valeurs de configuration de VM à $_POST['virtual_machine']
		 * 		associer les valeurs de configuration de l'application à $_POST['application_configuration']
		 * 
		 *	 Utiliser uniquement $jsonConfig pour l'attribution de valeur
		 */
		/*
		foreach($jsonConfig as $key => $value) {
			$jsonConfig['azure_connexion'][$key] = $_POST['azure_connexion'][$key];
			$jsonConfig['virtual_machine'][$key] = $_POST['virtual_machine'][$key];
			$jsonConfig['application_configuration'][$key] = $_POST['application_configuration'][$key];
		}
		*/
		foreach($jsonConfig as $key => $value) {
			if ($key == 'TimerDuration' && is_numeric($value) && $value > 0) {
				$jsonConfig[$key] = $_POST[$key];
			} else {
				$jsonConfig[$key] = $_POST[$key];
			}
		}
		foreach($jsonAzure as $key => $value) {
			$jsonAzure[$key] = $_POST[$key];
		}
		
		/**
		 * 	écrasement des valeurs dans les fichiers json
		 * 
		 */
		$jsonString = json_encode($jsonConfig);
		setConfigFile("config", $jsonString);

		$jsonString = json_encode($jsonAzure);
		setConfigFile("azure", $jsonString);

		header( "Location: config.php" );
	}
?>
