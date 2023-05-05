<?php

	/**
	 *  Fichier d'accueil
	 * 	Permet d'installer tout les packages requis et vérifier les autorisations
	 * 	Les packages à installer se trouvent dans resources/requirements.txt
	 * 
	 * 		Prévu : 
	 * 			Vérification si l'environnement virtuel existe déjà ou pas
	 * 			Si existe déjà => rien faire, sinon tout installer
	 */

	/**
	 *  Définition des données globales et de configuration
	 * 
	 */

	include_once("function.php");
	set_time_limit(180);

	if (session_status() == PHP_SESSION_NONE) {
		session_start();
	}
	if(!isset($_SESSION['python'])){

		$_SESSION['python'] = 'python';
	}
	if(!isset($_SESSION['pip'])){
		$_SESSION['pip'] = 'pip3.11';
	}
	if(!isset($_SESSION['typeAccount'])){

		$_SESSION['typeAccount'] = 'none';
	}
	$typeAccount = $_SESSION['typeAccount'];
	$dataVirtualMachine = getConfigFile('config');
	$azureData = getConfigFile('azure');
	$python = $_SESSION['python'];
	$pip = $_SESSION['pip'];
	$os = getOS();
	$nameVM = $dataVirtualMachine['name_virtual_machine'];
	$typeFunc = '';
	$pathToMain =  __DIR__ . DIRECTORY_SEPARATOR . '..';
	$pathToVenv = $pathToMain . DIRECTORY_SEPARATOR . "scripts". DIRECTORY_SEPARATOR . "vmazureenv";
	$pathToRequire = $pathToMain . DIRECTORY_SEPARATOR . "resources". DIRECTORY_SEPARATOR . "requirements.txt";

?>

<html>
	<head>
		<title>index</title>
	</head>
	<body>	
		<legend>Main Page</legend>

		<form action="main.php" method="post">
		 <BR> <BR>
		 	<?php
				if($typeAccount != 'none') {
					echo "<legend>Creation de VM</legend>";
                    echo "<a href=$typeAccount"."VM.php>here</a>";
					echo "<BR> <BR>";
				}
			?>
            <legend>Modifier Valeurs par defaut</legend>
            <a href="config.php">here</a>
            <BR> <BR>
			<form action="main.php" method="post">

			<legend>VM à utiliser pour les actions suivantes</legend>
				<input type="text" name="nameVM" value= <?php 
															if(isset($_POST['nameVM'])) {
																echo $_POST['nameVM'];
															}
														?>>
            <BR> <BR>

			 <legend>Lister les VM et leurs ressources</legend>
				<input type="submit" name="type" value="list"/>
            <BR> <BR>

            <legend>Supprimer VM</legend>
				<input type="submit" name="type" value="delete"/>
            <BR> <BR>

			<legend>Redemarrer VM</legend>
			<input type="submit" name="type" value="restart"/>
            <BR> <BR>

			<legend>Demarrer VM</legend>
            <input type="submit" name="type" value="start"/>
            <BR> <BR>

			<legend>Arreter VM</legend>
            <input type="submit" name="type" value="stop"/>
            <BR> <BR>

			<input type="hidden" name="form" />
		</form>

	<?php

		if(isset($_POST['form'])) {

			if(!isset($_POST['type'])) {
			
				return;

			}

			if(!isset($_POST['nameVM'])) {
			
				return;

			}
			$nameVM = $_POST['nameVM'];
			$typeFunc = $_POST['type'];
			if($os == 'Windows') {
				
				$command = "$pathToVenv/Scripts/python $pathToMain/scripts/manageVM.py $nameVM $typeFunc";

			} else {
				
				$command = 'sudo -S ' . $pathToVenv . '/bin/python3 ' . $pathToMain . '/scripts/manageVM.py ' . $nameVM . ' ' . $typeFunc . ' <<< "'. $sudo . '"';
				
			}

			$output = executeCommand($command);
			$output = str_replace("Microsoft", "<br>Microsoft", $output);
			echo "Resultat du script : <br> $output";
		}
	?>
		<BR>
		<a href="login.php">Connexion</a>
		<BR>
		<a href="config.php">page de modification des valeurs par defaut</a>
		<BR>	
	</body>
</html>