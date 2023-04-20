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
				<BR>Selection de l'OS <BR>
				<select name="defaultOS" id="defaultOS-select">
					<option value="debian">Debian</option>
					<option value="ubuntu">Ubuntu</option>
					<option value="windowsDesktop">Windows 10</option>
					<option value="windowsServer">Windows Server</option>
				</select>
				<BR>Selection de la region <BR>
				<select name="defaultRegion" id="defaultRegion-select">
					<option value="westeurope">Europe Ouest</option>
					<option value="northeurope">Europe Nord</option>
					<option value="francecentral">France Centrale</option>
					<option value="eastus">USA Est</option>
					<option value="westus">USA Ouest</option>
					<option value="northcentralus">USA Nord</option>
					<option value="southcentralus">USA Sud</option>
					<option value="usa">USA</option>
				</select>
				<BR>Avec Interface Graphique (Aucune Incidence sur la suite, WIP)<BR>
				<select name="interface" id="defaultInterface-select">
					<option value="no">Non</option>
					<option value="yes">Oui</option>
				</select>
				<BR> Nom d'utilisateur : <BR>
				<?php
					$arrToSend['username'] = generateRandomUsername();
					echo "<input type=hidden name=username value=$arrToSend[username]>";
					echo $arrToSend['username'];
				?>
				<BR> Mot de passe : <BR>
				<?php
					$arrToSend['password'] = generateRandompassword();
					echo "<input type=hidden name=password value=$arrToSend[password]>";
					echo $arrToSend['password'];
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
