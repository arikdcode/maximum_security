class KnightSaberIdle : Actor
{
	
	Default
	{
		//$Category Monsters
		//$Title "KnightSaberIdle"
		Health 280;
		Radius 20;
		Height 60;
		Mass 150;
		Speed 8;
		//PainChance 0;
		//Monster;
		Scale 0.667;
		//+MISSILEMORE;
		+DONTHARMCLASS;
		+NOGRAVITY;
		+FLOAT;
		+AVOIDMELEE;
		//+NOINFIGHTING;
		+NOTARGET;
		+BUDDHA
		+NOPAIN
		//PainSound "Cacomancer/pain";
		//DeathSound "Cacomancer/death";
		//ActiveSound "Cacomancer/active";
		//Obituary "%o was killed by a Cacomancer.";
	}
	States
	{
	Spawn:
		DKNO ABCD 2 BRIGHT;
		DKNO D 35 BRIGHT;
		DKNO ABCD 2 BRIGHT;
		DKNO D 10 BRIGHT;
		DKNO ABCD 2 BRIGHT;
		DKNO D 140 BRIGHT;
		Loop;
	}
}

class KnightSaberIgnite : Actor
{
	
	Default
	{
		//$Category Monsters
		//$Title "KnightSaberIntro"
		Health 280;
		Radius 20;
		Height 60;
		Mass 150;
		Speed 8;
		//PainChance 0;
		//Monster;
		Scale 0.667;
		//+MISSILEMORE;
		+DONTHARMCLASS;
		+NOGRAVITY;
		+FLOAT;
		+AVOIDMELEE;
		//+NOINFIGHTING;
		+NOTARGET;
		+BUDDHA
		+NOPAIN
		//PainSound "Cacomancer/pain";
		//DeathSound "Cacomancer/death";
		//ActiveSound "Cacomancer/active";
		//Obituary "%o was killed by a Cacomancer.";
		SeeSound "SaberLight";
	}
	States
	{
	Spawn:
		DKNS E 1 A_StartSound("SaberLight");
		DKNS EFGHIJK 3 BRIGHT ;
		goto see;
	 See:
		DKNS LMN 2 BRIGHT ;
		loop;
	}
}