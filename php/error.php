<?php
	/**
	 *  Fichier de gestion d'erreur
	 * 	Permet de : 
	 * 		///
	 * 
	 * 		Prévu : 
	 * 			Affichage de l'erreur
	 * 			Affichage des possibles façon de régler l'erreur
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
?>

<html>
	<head>
		<title>Error</title>
	</head>
	<body>	
		Credit Insuffisant, connectez-vous avec un autre compte ou recharger votre compte.
		<BR><BR><BR><BR>
		<a href="config.php">page de modification des valeurs par defaut</a>
		<BR>		
		<a href="login.php">retour page de connexion</a>
		<BR>	
	</body>
</html>
