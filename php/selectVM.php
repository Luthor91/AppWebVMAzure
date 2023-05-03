<?php

	/**
	 *  Fichier de sélection de la VM sur le Cloud Azure
	 * 	Permet de sélectionner les paramètres de la VM à créer :
	 * 		Système d'exploitation
	 * 		Région
	 * 		Avec ou Sans interface graphique (non fonctionnel)
	 * 		
	 * Nom d'utilisateur et Mot de Passe créées aléatoirement
	 * 
	 * 		Prévu : 
	 * 			Sélection du nom de la VM
	 * 			Sélection du groupe de ressource de la VM
	 * 			
	 */

	/**
	 *  Définition des données globales et de configuration
	 * 
	 */

	if (session_status() == PHP_SESSION_NONE) {
		session_start();
	}
	include_once("function.php");
	$jsonArray = getConfigFile('config');
?>

<html>
	<head>
		<title>selectVM</title>
	</head>
	<body>	
		<form action="createVM.php" method="post">
			<legend>Selection de la VM</legend>
			<p> 
				<BR>Selection du nom de la machine <BR>
				<input type="text" name="name_virtual_machine" />	
				<BR><BR>Selection de l'OS <BR>
				<select name="operating_system" id="operating_system-select">
					<option value="debian">Debian</option>
					<option value="ubuntu">Ubuntu</option>
					<option value="windowsDesktop">Windows 10</option>
					<option value="windowsServer">Windows Server</option>
				</select>
				<BR><BR>Selection de la region <BR>
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
				<BR><BR>Avec Interface Graphique (Aucune Incidence sur la suite, WIP)<BR>
				<select name="interface" id="defaultInterface-select">
					<option value="no">Non</option>
					<option value="yes">Oui</option>
				</select>
				<BR><BR> Nom d'utilisateur : <BR>
				<?php
					$arrToSend['username'] = generateRandomUsername();
					echo "<input type=hidden name=username value=$arrToSend[username]>";
					echo $arrToSend['username'];
				?>
				<BR><BR> Mot de passe : <BR>
				<?php
					$arrToSend['password'] = generateRandompassword();
					echo "<input type=hidden name=password value=$arrToSend[password]>";
					echo $arrToSend['password'];

					echo "<input type=hidden name=username value=$arrToSend[username] />";
					echo "<input type=hidden name=password value=$arrToSend[password] />";
				?>
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
