Class Turret_Head : Actor
{
	Default
	{
		Radius 20;
		Height 16;
		Health 300;
		Scale 0.75;
		PainChance 192;
		PainThreshold 50;
		SeeSound "Turret/Sight";
		DeathSound "Turret/Death";
		PainSound "Turret/Pain";
		Obituary "%o was fried by a spider turret.";
		Tag "Spider Turret";
		BloodType "Turret_Blood";

		Monster;
		+DONTTHRUST
		+AMBUSH
		+NOTARGET
		+NOINFIGHTING
	}

	States
	{
		LostTarget:
			UNKN A 0 A_PlaySound ("Turret/Idle");
			UNKN A 20 A_ClearTarget;
			Goto Idle;
		Spawn:
			UNKN A 10 A_LookEx (LOF_DONTCHASEGOAL, 0, 1024);
			Loop;
		Idle:
			UNKN A 10 A_LookEx (LOF_DONTCHASEGOAL, 0, 1024, 0, 360);
			Loop;
		See:
			UNKN A 10;
		See2:
			UNKN A 0 A_JumpIfInTargetLOS ("See3", 0, JLOSF_DEADNOJUMP); // stop shooting if target is killed
			Goto LostTarget;
		See3:
			UNKN A 0 A_CheckSight ("LostTarget");
			UNKN AAAAAAAAA 1 A_FaceTarget (3, 3);
			UNKN A 0 A_SpawnProjectile ("Turret_Plasma", 6, 0, 0, CMF_AIMDIRECTION|CMF_OFFSETPITCH, Pitch);
			Goto See2;
		Pain:
			UNKN A 0
			{
				bNOPAIN = TRUE;
				A_SpawnItem ("Turret_Impact_Spark", 32, 6);
				A_Pain();
			}
			UNKN A 0 A_Jump (128, "PainSpin2");
		PainSpin:
			UNKN AAAAAAAA 1 A_SetAngle (Angle+10);
			UNKN A 0 
			{
				bNOPAIN = FALSE;
			}
			Goto See2;
		PainSpin2:
			UNKN AAAAAAAA 1 A_SetAngle (Angle-10);
			UNKN A 0 
			{
				bNOPAIN = FALSE;
			}
			Goto See2;
		Death:
			TNT1 A -1
			{
				A_ScreamAndUnblock();
				A_SpawnItem ("Turret_Explosion", 0, 6);
				A_SpawnItem ("Turret_Blood_Fountain", 0, 6);
				A_SpawnItem ("Turret_Death_Sparks", 0, 8);
			}
			Stop;
	}
}

Class Turret_Base : Actor
{
	//$Category Monsters
	//$Title Spider Turret
	
	Default
	{
		Radius 20;
		Height 32;
		Scale 0.75;
	  
		+SOLID
		+ACTLIKEBRIDGE
	}

	States
	{
		Spawn:
			UNKN A 0 NoDelay A_SpawnItem ("Turret_Head", 0, 32);
			UNKN A -1 A_SpawnItem ("Turret_Floor_Wires");
			Stop;
	}
}

Class Turret_Explosion : Actor
{
	Default
	{
		RenderStyle "Add";
		+NOINTERACTION
	}
	
	States
	{
	Spawn:
		MISL B 8 NoDelay Bright A_StartSound ("weapons/rocklx");
		MISL C 6 Bright;
		MISL D 4 Bright;
		Stop;
	}
}

Class Turret_Plasma : PlasmaBall
{
	Default
	{
		Scale 0.75;
		Decal "PlasmaScorch";
		SeeSound "Turret/Shoot";
	}

	States
	{
 	Spawn:
		TNT1 A 2;
		TNT1 A 0 A_SpawnItemEx ("Turret_Plasma_Flash", 0, 0, 0, 0, 0, 0, 0, SXF_TRANSFERTRANSLATION);
		TNT1 A 1;
	Spawn2:
		PLSS AB 6 Bright;
		Loop;
	}
}

// Muzzle flash effect on weapon barrel
Class Turret_Plasma_Flash : Actor
{
	Default
	{
		RenderStyle "Add";
		Scale 0.4;
		+ZDOOMTRANS
		+NOINTERACTION
		+FLATSPRITE
	}
	
	States
	{
	Spawn:
		PLSE A 0 NoDelay Bright A_SetPitch (90);
		PLSE ABCDE 2 Bright;
		Stop;
	}
}

// spurt of gore upon death
Class Turret_Blood_Fountain : Actor
{
	Default
	{
		ReactionTime 10;
		+NOINTERACTION
	}

	States
	{
		Spawn:
			TNT1 A 0 NoDelay A_PlaySound ("misc/gibbed");
		Spawn2:
			TNT1 A 1;
			TNT1 AAA 0 A_SpawnItemEx ("BloodSplatter", 0, 0, 0, random(1, 5), 0, random(5, 15), random(0, 360), SXF_USEBLOODCOLOR|SXF_CLIENTSIDE);
			TNT1 A 0 A_CountDown;
			Loop;
	}
}

Class Turret_Floor_Wires : Actor
{
	Default
	{
		Scale 0.75;
		+FLATSPRITE
	}

	States
	{
		Spawn:
			3DTF A -1 NoDelay A_SetAngle (randompick (0, 90, 180, 270));
	}
}

// Turret base randomly sparks for a time after the head is destroyed
Class Turret_Death_Sparks : Spark
{
	Default
	{
		ReactionTime 20;
	}

	States
	{
		Spawn:
			TNT1 A random (35, 175) NoDelay 
			{
				A_SetAngle (random(0, 360));
				Thing_Activate (0);
				A_CountDown ();
			}
			Loop;
	}
}

Class Turret_Impact_Spark : Spark
{
	States
	{
		Spawn:
			TNT1 A 1 NoDelay Thing_Activate (0);
			Stop;
	}
}

// small chance to spawn some sparks when bleeding
Class Turret_Blood : Blood
{
	States
	{
	Spawn:
		BLUD C 0 NoDelay A_SpawnItemEx ("Turret_Impact_Spark", 0, 0, 0, 0, 0, 0, 0, 0, 208);
		BLUD CBA 8;
		Stop;
	}
}