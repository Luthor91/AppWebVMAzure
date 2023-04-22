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
	
	$azureData = getConfigFile('azure');
	$python = $_SESSION['python'];
	$pip = $_SESSION['pip'];
	$os = getOS();
?>

<html>
	<head>
		<title>index</title>
	</head>
	<body>	
		<legend>Configurations</legend>

		<form action="index.php" method="post">
		 <BR> <BR>
			<legend>Renseignez un mot de passe administateur ici si vous utilisez Linux, il sera nécessaire pour effectuer des commandes sudo</legend>
			<BR>
			<input type="password" name="sudo" value="" />
			 <BR> <BR>
			<legend>Cliquez sur le bouton ci-dessous pour installer les fichiers necessaires</legend>
			<BR>
			<input type="submit" name="install" value="Installation" />	
		</form>
		
		<?php
		if(isset($_POST['install'])){
			/**
			 * 	Définition des chemins principaux utilisés
			 * 
			 */
			$pip_versions = array("pip3.11", "pip3", "pip");
			$python_versions = array("python3", "python");
			$pathToMain =  __DIR__ . DIRECTORY_SEPARATOR . '..';
			$pathToVenv = $pathToMain . DIRECTORY_SEPARATOR . "scripts". DIRECTORY_SEPARATOR . "vmazureenv";
			$pathToRequire = $pathToMain . DIRECTORY_SEPARATOR . "resources". DIRECTORY_SEPARATOR . "requirements.txt";
			$output = '';

			if ($os == "Windows"){
				/**
				 * Code pour une machine physique Windows
				 * 
				 */
				exec("$python -m venv $pathToVenv vmazureenv");
				exec($pathToVenv . '/Scripts/activate.bat');
				
				foreach ($pip_versions as $version) {
					$pip = exec("where $version");
					if (!empty($pip)) {
						$pip = exec("$version --version");
						$pip = $version;
						break;
					}
				}
				exec("$pathToVenv/Scripts/$pip install -r $pathToMain/resources/requirements.txt");

			} else {
				/**
				 * Code pour une machine physique Linux (testé sur Ubuntu)
				 * 	Installation de l'environnement virtuel, attribution des droits
				 */
				$sudo = $_POST['sudo'];
				$_SESSION['sudo'] = $sudo;
				foreach ($python_versions as $version) {
					$python = exec("which $version");
					if (!empty($python)) {
						break;
					}
				}
				$python = pathinfo(basename($python), PATHINFO_FILENAME);
				shell_exec('sudo -S chmod -R a+rwx ' . $pathToMain . ' <<< "'. $sudo . '"');
				$r = shell_exec("sudo -S  $python" . ' -m venv ' . $pathToMain . 'scripts/vmazureenv vmazureenv <<< "'. $sudo . '"');
				shell_exec('sudo -S chmod -R a+rwx ' . $pathToVenv . ' <<< "'. $sudo . '"');
				shell_exec("source $pathToVenv/bin/activate");
				foreach ($pip_versions as $version) {
					$pip = exec("which $version");
					if (!empty($pip)) {
						$pip = shell_exec("$version --version");
						$pip = $version;
						break;
					}
				}
				
				
				shell_exec("sudo -S $pathToEnv/bin/$pip install -r $pathToRequire" . ' <<< "'. $sudo . '"');
			}
			header("Location: login.php");
		} else {
			echo "<br>Temps d'installation estime : 120 secondes pour l'installation complète<br>";

		}
			
		?>
		<BR>
		<a href="login.php">Connexion</a>
		<BR>
		<a href="config.php">page de modification des valeurs par defaut</a>
		<BR>	
	</body>
</html>