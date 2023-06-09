<?php
	/**
	 *  Fichier de sélection de la VM sur le Cloud Azure
	 * 	Permet de vérifier les paramètres de la VM à créer
	 * 	Les paramètres par défauts se trouvent aussi dans data/config.json
	 * 
	 * 		Prévu : 
	 * 			Affichage du nom de la VM
	 * 			Affichage du groupe de ressource de la VM	
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
	$arrToSend = array();
?>

<html>
	<head>
		<title>defaultVM</title>
	</head>
	<body>	
		<legend>VM par defaut</legend>
		<p> 
			<?php
				/**
				 * 	Gestion des erreurs à revoir
				 * 
				 */

				 echo "Nom Machine Virtuelle : ";

				if(isset($jsonArray['name_virtual_machine'])){
					echo $jsonArray['name_virtual_machine'];
					$arrToSend['name_virtual_machine'] = $jsonArray['name_virtual_machine'];
				} else {
					echo "Erreur";
				}	

				echo "<BR>OS selectionne : ";

				if(isset($jsonArray['operating_system'])){
					echo $jsonArray['operating_system'];
					$arrToSend['operating_system'] = $jsonArray['operating_system'];
				} else {
					echo "Erreur";
				}

				echo "<BR>Region selectionnee : ";

				if(isset($jsonArray['location'])){
					echo $jsonArray['location'];
					$arrToSend['location'] = $jsonArray['location'];
				} else {
					echo "Erreur";
				}

				if(!str_starts_with($jsonArray['defaultOS'], 'w')){
					/**
					 * Si la machine virtuelle sélectionné est une Linux
					 * 
					 */
					echo "<BR>Type de connexion : SSH";
					$arrToSend['conn'] = 'ssh';
				} else {
					/**
					 * Si la machine virtuelle sélectionné est une Windows
					 * 
					 */
					echo "<BR>Type de connexion : RDP";
					$arrToSend['conn'] = 'rdesktop';
				}

				echo "<BR> Interface graphique : Non <BR>";
				$arrToSend['interface'] = 'no';

				echo "<BR> Nom d'utilisateur :";
				$arrToSend['username'] = generateRandomUsername();
				echo $arrToSend['username'];
				
				echo "<BR> Mot de passe :";
				$arrToSend['password'] = generateRandomPassword();
				echo $arrToSend['password'];
			?>
		</p>
		<form action="createVM.php" method="post">

			<?php
				/**
				 * 	Envoie des données de la VM
				 * 
				 */

				foreach ($arrToSend as $key => $value) {
					echo "<input type=hidden name=$key value=$value>";
				}
			?>

			<input type="submit" name="form" value="Envoyer" />	
		</form>
		<BR><BR>
		<a href="config.php">page de modification des valeurs par defaut</a>
		<BR>		
		<a href="login.php">retour page de connexion</a>
		<BR>		
	</body>
</html>
