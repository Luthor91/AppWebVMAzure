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
		<form action="main.php" method="post">
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
				<select name="operating_system" id="operating_system-select">
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
				<select name="location" id="location-select">
					<option disabled>─────Europe─────</option>
					<option value="francecentral">France Centrale</option>
					<option value="westeurope">Europe de l'Ouest</option>
					<option value="northeurope">Europe du Nord</option>
					<option value="germanywestcentral">Allemagne Nord Ouest</option>
					<option value="switzerlandnorth">Suisse Nord</option>
					<option value="uksouth">Royaume-Uni Sud</option>
					<option value="ukwest">Royaume-Uni Est</option>
					<option value="norwayeast">Norvège Est</option>
					<option value="swedencentral">Suède Centre</option>
					<option value="polandcentral">Pologne Centre</option>

					<option disabled>────Amerique──────</option>
					<option value="eastus">USA Est 1</option>
					<option value="eastus2">USA Est 2</option>
					<option value="centralus">USA Centre</option>
					<option value="westcentralus">USA Ouest Central</option>
					<option value="westus">USA Ouest 1</option>
					<option value="westus2">USA Ouest 2</option>
					<option value="westus3">USA Ouest 3</option>
					<option value="northcentralus">USA Nord</option>
					<option value="southcentralus">USA Sud</option>
					<option value="canadacentral">Canada Central</option>
					<option value="canadaeast">Canada Est</option>

					<option disabled>────Asie─────</option>
					<option value="southeastasia">Asie Sud-Est</option>
					<option value="eastasia">Asie Est</option>
					<option value="centralindia">Inde Centre</option>
					<option value="southindia">Inde Sud</option>
					<option value="westindia">Inde Ouest</option>
					<option value="jioindiawest">Jio Inde Ouest ?</option>
					<option value="brazilsouth">Bresil Sud</option>
					<option value="koreacentral">Corée Centre</option>
					<option value="koreasouth">Corée Sud</option>
					<option value="japaneast">Japon Est</option>
					<option value="japanwest">Japon Ouest</option>

					<option disabled>────Moyen Orient─────</option>
					<option value="uaenorth">Etat Arabes Unis Nord</option>
					<option value="australiacentral">Australie Centre</option>
					<option value="qatarcentral">Qatar Centre</option>
					
					<option disabled>────Oceanie─────</option>
					<option value="australiaeast">Australie Est</option>
					<option value="australiasoutheast">Australie Sud-Est</option>

					<option disabled>────Afrique─────</option>
					<option value="southafricanorth">Sud Afrique Nord</option>
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
			if(empty($_POST[$key])){
				continue;
			}
			if ($key == 'TimerDuration' && is_numeric($value) && $value > 0) {
				$jsonConfig[$key] = $_POST[$key];
			} else {
				$jsonConfig[$key] = $_POST[$key];
			}
		}
		foreach($jsonAzure as $key => $value) {
			if(empty($_POST[$key])){
				continue;
			}
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
