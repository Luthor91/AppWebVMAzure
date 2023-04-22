<?php
	/**
	 *  Fichier de fonction
	 * 	Permet d'appeler des fonction utilitaires
	 * 			
	 */

	/**
	 *  Définition des données globales et de configuration
	 * 
	 */
	if (session_status() == PHP_SESSION_NONE) {
		session_start();
	}

	/**
	 * isValidVMname
	 *	: Permet de savoir si le nom de la machine virtuelle est valide
	* 
	* @param  string $name nom de la machine virtuelle
	* @return bool code retour 
	*/
	function isValidVMname(String $vm_name): bool {
		// Vérifie que le nom ne dépasse pas la longueur maximale autorisée
		if (strlen($vm_name) > 64) {
			return false;
		}

		// Vérifie que le nom ne contient que des caractères autorisés
		if (!preg_match('/^[a-zA-Z0-9_-]*$/', $vm_name)) {
			return false;
		}

		// Vérifie que le nom ne commence ni ne se termine par un trait d'union
		if (substr($vm_name, 0, 1) == '-' || substr($vm_name, -1) == '-') {
			return false;
		}
		
		// Vérifie que le nom ne contienne pas des mots interdits  
		$reservedWords = ['windows'];
		if (in_array(strtolower($vm_name), $reservedWords)) {
			return false;
		}

		return true;
	}

	/**
	 * setConfigFile
	 *	: Permet d'insérer des données JSON dans un fichier
	* 
	* @param  string $nameFile nom du fichier
	* @param  string $jsonString données json à insérer
	* @return int|false code retour 
	*/
	function setConfigFile(String $nameFile, String $jsonString): int|false {
		$configFilePath = __DIR__ . DIRECTORY_SEPARATOR . '..' . DIRECTORY_SEPARATOR . 'data' . DIRECTORY_SEPARATOR . $nameFile.'.json';
		$r = file_put_contents($configFilePath, $jsonString);
		return $r;
	}

	/**
	 * getConfigFile
	 *	: Permet de récupérer des données JSON d'un fichier
	* 
	* @param  string $nameFile nom du fichier
	* @return Array Données du fichier
	*/
	function getConfigFile(String $nameFile) : Array {
		$configFilePath = __DIR__ . DIRECTORY_SEPARATOR . '..' . DIRECTORY_SEPARATOR . 'data' . DIRECTORY_SEPARATOR . $nameFile.'.json';
		if(!file_exists($configFilePath)){
			file_put_contents($configFilePath, array(''));
		}
		$data = file_get_contents($configFilePath);
		$array = json_decode($data, true);
		if($nameFile == 'config'){
			if(empty($array)){
				$array = array(
					'TimerDuration' => '10',
					'startTimer' => 'conn',
					'defaultOS' => 'debian',
					'defaultRegion' => 'westeurope',
					'ip_address' => 'ip_address',
					'name_virtual_machine' => 'VMname'
				);
			}
		} elseif($nameFile == 'azure') {
			if(empty($array)){
				$array = array(
					'TENANT' => 'null',
					'CLIENT' => 'null',
					'SECRET' => 'null',
					'SUBSCRIPTION' => 'null'
				);
			}
		}
		return $array;
	}

	/**
	 * updateConfigFile
	 *	: Permet de mettre à jour des données JSON d'un fichier
	* 
	* @param  string $nameFile nom du fichier
	* @param  array $vals valeurs à mettre à jour
	* @return bool code retour 
	*/
	function updateConfigFile(String $nameFile, Array $vals) : bool {
		$configFilePath = __DIR__ . DIRECTORY_SEPARATOR . '..' . DIRECTORY_SEPARATOR . 'data' . DIRECTORY_SEPARATOR . $nameFile.'.json';
		if(!file_exists($configFilePath)){
			file_put_contents($configFilePath, array(''));
		}
		$data = file_get_contents($configFilePath);
		$array = json_decode($data, true);
		foreach ($vals as $key => $value) {
			$array[$key] = $value;
		}
		$array = json_encode($array);
		$res = file_put_contents($configFilePath, $array);
		return $res;
	}

	/**
	 * execInBackground
	 *	: Permet d'exécuter une commande shell de manière asynchrone
	* 
	* @param  string $cmd commande à exécuter
	* @return mixed code retour 
	*/
	function execInBackground(String $cmd): mixed {
		$logFilePath = __DIR__ . DIRECTORY_SEPARATOR . '..' . DIRECTORY_SEPARATOR . 'resources' . DIRECTORY_SEPARATOR . 'log.txt';
		if (substr(php_uname(), 0, 7) == "Windows"){
			$r = pclose(popen("start /B ". $cmd." >> " . $logFilePath, "r")); 
		}
		else {
			$r = shell_exec("$cmd >> $logFilePath 2>&1 &");
		}
		return $r;
	}


	/**
	 * getOS
	 *	: Permet de connaitre l'OS de la machine actuelle
	* 
	* @return string code retour 
	*/
	function getOS(): String {
		if(substr(php_uname(), 0, 7) == "Windows"){
			return "Windows";
		}
		return "Linux";
	}

	/**
 	* get_string_between
	*	: Permet de récupérer une string situé entre deux autres string
	* 
	* @param  string $string chaine à traiter
	* @param  string $start chaine de début
	* @param  string $end chaine de fin
	* @return string chaine à récupérer
	*/
	function get_string_between($string, $start, $end): String {
		$string = ' ' . $string;
		$ini = strpos($string, $start);
		if ($ini == 0) {
			return '';
		}
		$ini += strlen($start);
		$len = strpos($string, $end, $ini) - $ini;

		return substr($string, $ini, $len);
	}

	/**
 	* generateRandomUsername
	*	: Génère un nom d'utilisateur aléatoire valide pour Azure Cloud
	* 
	* @param  int $length longueur du nom d'utilisateur, par défaut à 10
	* @return string nom d'utilisateur
	*/
	function generateRandomUsername(int $length = 10): String {
		$length = rand(5, 20);
		$consonants = 'bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ';
		$vowels = 'aeiouAEIOU';
		$specialChars = '_-';
		$string = '';
	
		// Ajoute la première lettre majuscule
		$string .= strtoupper($consonants[rand(0, strlen($consonants) - 1)]);
	
		// Génère la chaîne de caractères
		do {
			// Ajoute une consonne
			$string .= $consonants[rand(0, strlen($consonants) - 1)];
			// Ajoute au moins 2 voyelles d'affilée
			$string .= str_repeat($vowels[rand(0, strlen($vowels) - 1)], 2);
			// Ajoute une consonne ou une voyelle
			if (strlen($string) < $length - 2) {
				$string .= rand(0, 1) ? $consonants[rand(0, strlen($consonants) - 1)] : $vowels[rand(0, strlen($vowels) - 1)];
			}
		} while (strlen($string) < $length);
	
		// Ajoute le caractère spécial aléatoirement
		$pos = rand(1, strlen($string) - 2);
		$string = substr_replace($string, $specialChars[rand(0, strlen($specialChars) - 1)], $pos, 0);
	
		// Vérifie que le caractère spécial est suivi d'une lettre majuscule
		if ($string[$pos + 1] != strtoupper($string[$pos + 1])) {
			$string = substr_replace($string, strtoupper($string[$pos + 1]), $pos + 1, 1);
		}
	
		// Vérifie que la chaîne ne contient pas une seule voyelle d'affilée
		while (preg_match('/[aeiou]{2,}/i', $string) == false) {
			$pos = rand(1, strlen($string) - 2);
			$string = substr_replace($string, $vowels[rand(0, strlen($vowels) - 1)], $pos, 1);
		}
	
		return $string;
	}


	/**
 	* generateRandomPassword
	*	: Génère un mot de passe aléatoire valide pour Azure Cloud
	* 
	* @param  int $length longueur du nom d'utilisateur, par défaut à 12
	* @param  bool $use_uppercase utilise des majuscules, par défaut à true
	* @param  bool $use_numbers utilise des nombres, par défaut à true
	* @param  bool $use_symbols utilise des caractères spéciaux, par défaut à true
	* @return string mot de passe
	*/
	function generateRandomPassword(int $length = 12, bool $use_uppercase = true, bool $use_numbers = true, bool $use_symbols = true): String {
		// Définition des caractères possibles pour chaque type de caractère
		$lowercase_chars = 'abcdefghijklmnopqrstuvwxyz';
		$uppercase_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
		$number_chars = '0123456789';
		$symbol_chars = '!@#$%^&*()_+-={}[];\',./?';

		// Initialisation de la chaîne de caractères pouvant être utilisés pour générer le mot de passe
		$chars = $lowercase_chars;
		if ($use_uppercase) {
			$chars .= $uppercase_chars;
		}
		if ($use_numbers) {
			$chars .= $number_chars;
		}
		if ($use_symbols) {
			$chars .= $symbol_chars;
		}

		// On s'assure que le mot de passe ne commence ni ne termine par un caractère spécial
		do {
			$password = $chars[random_int(0, strlen($chars) - 1)];
			for ($i = 1; $i < $length - 1; $i++) {
				$password .= $chars[random_int(0, strlen($chars) - 1)];
			}
			$password .= $chars[random_int(0, strlen($chars) - 1)];
		} while (strpos($symbol_chars, $password[0]) !== false || strpos($symbol_chars, $password[$length - 1]) !== false);

		// On s'assure que le mot de passe ne contient pas une majorité de caractères spéciaux
		$symbol_count = 0;
		for ($i = 0; $i < $length; $i++) {
			if (strpos($symbol_chars, $password[$i]) !== false) {
				$symbol_count++;
			}
		}
		if ($symbol_count > ($length / 2)) {
			return generateRandomPassword($length, $use_uppercase, $use_numbers, $use_symbols);
		}
	
		return $password;
	}
	
?>
