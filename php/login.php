<?php

	/**
	 *  Fichier de connexion
	 * 	Permet de se connecter au site, pas au Cloud Azure
	 * 	Les logins et mots de passes se trouvent dans ReadMe.txt
	 * 
	 * 		Prévu : 
	 * 			Connexion au site Azure au lieu de comptes écrits en dur
	 */

	/**
	 *  Définition des données globales et de configuration
	 * 
	 */

	if (session_status() == PHP_SESSION_NONE) {
		session_start();
	}
	if(!isset($_SESSION['typeAccount'])){

		$_SESSION['typeAccount'] = 'none';
	}
	include_once("function.php");
?>

<html>
	<head>
		<title>Connexion</title>
	</head>

	<body>
		<form action="login.php" method="post">
			<BR>
				<legend>Connexion</legend>
			<BR>
				<legend>Username</legend>
				<input type="text" name="username" placeholder="username"/>
			<BR><BR>
				<legend>Password</legend>
				<input type="password" name="password" placeholder="password"/>
			<BR><BR>
				<input type="submit" name="login" value="Connexion" />
			<BR><BR>
		</form>
		<a href="config.php">page de configuration</a>
		<BR>		
	</body>
</html>

<?php



	if(isset($_POST['login'])){

		if( $_POST['username'] == 'boss' && $_POST['password'] == 'boss' ) {
			
			$_SESSION['typeAccount'] = 'select';
			header( "Location: main.php" );

		} elseif( $_POST['username'] == 'hitman' && $_POST['password'] == 'hitman' ) {

			$_SESSION['typeAccount'] = 'default';
			header( "Location: main.php" );

		}  elseif( $_POST['username'] == 'crook' && $_POST['password'] == 'crook' ) {
			
			$_SESSION['typeAccount'] = 'none';
			header( "Location: error.php" );

		}else {

			$_SESSION['typeAccount'] = 'none';
			header( "Location: error.php" );

		}
	}

?>
