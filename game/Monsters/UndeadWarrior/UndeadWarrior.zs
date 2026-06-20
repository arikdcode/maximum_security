class UndeadWarrior : Knight
{
	//$Title Undead Warrior
	//$Category Monsters/Custom/Undead

	Default
	{
		Health 175;
		Speed 6;
		Radius 22;
		Height 70;
		Scale 0.9;
		DropItem "";
	
		+TELESTOMP
		
		SeeSound "UndeadWarrior/Sight";
		AttackSound "monsters/KNIGHTATTK";
		PainSound "UndeadWarrior/Pain";
		DeathSound "UndeadWarrior/Death";
		ActiveSound "UndeadWarrior/Active";
		
		Tag "Undead Warrior";
	}
	
	States
	{
	Spawn:
		KNIX A 10 A_Look;
		Loop;
	See:
		KNIX AABBCCDD 3 A_Chase;
		Loop;
	Melee:
		KNIX E 10 A_FaceTarget;
		KNIX F 0 A_PlaySound ("FighterPunchMiss");
		KNIX F 8 A_FaceTarget;
		KNIX G 8 A_CustomMeleeAttack (3*random(1,10), "FighterAxeHitThing");
		Goto See;
	RepeatAttack:
		KNIX E 0 A_CheckSight ("See");
	Missile:
		KNIX E 10 A_FaceTarget;
		KNIX F 0 A_PlaySound ("FighterPunchMiss");
		KNIX F 8 A_FaceTarget;
		KNIX G 8 A_SpawnProjectile ("UndeadWarriorAxe", 32, 0, randompick (-5, 0, 5));
		KNIX G 0 A_Jump (96, "RepeatAttack");
		Goto See;
	Pain:
		KNIX H 3;
		KNIX H 3 A_Pain;
		Goto See;
	Death:
		KNIX A 0
		{
			bSPRITEFLIP = random (0, 1);
		}
		KNIX I 0 A_SpawnItemEx ("BishopPuff", 0, 0, 48, 0, 0, 0.5);
		KNIX I 0 A_PlaySound ("UndeadWarrior/Armor", 5);
		KNIX I 0 A_PlaySound ("FireDemonDeath", 6);
		KNIX I 0 A_PlaySound ("UndeadWarrior/Burn", 7);
		KNIX I 6 A_Scream;
		KNIX JJJJJJ 0 A_SpawnItemEx ("UndeadWarriorBit", 0, 0, 32, frandom (-2, 2), 0, frandom (4, 8), random (0, 360));
		KNIX J 6;
		KNIX K 6;
		KNIX L 6 A_NoBlocking;
		KNIX M 6;
		KNIX N 6 A_QueueCorpse;
		KNIX O -1;
		Stop;
	}
}


class UndeadWarriorAxe : KnightAxe
{
	Default
	{
		Speed 12;
		Damage 4;
		DamageType "Fire";
		Decal "AxeScorch";
		SeeSound "monsters/KNIGHTATTK";
		DeathSound "monsters/KNIGHTSTRIKE";
		
		+SPAWNSOUNDSOURCE
	}
	
	States
	{
		Spawn:
			KPAX A 0 Bright A_PlaySound("UndeadWarrior/Spin");
			KPAX ABC 3 Bright A_SpawnItemEx ("WraithFX2", -4, 0, 0, random (0, 2), 0, 0, randompick (-90, 90));
			Loop;
		Death:
			KPAX D 6 Bright A_SpawnItem ("LavaSmoke");
			KPAX EF 6 Bright;
			Stop;
		}
}



class UndeadWarriorBit : CorpseBit
{

	States
	{
	Spawn:
		TNT1 A 0 NoDelay A_QueueCorpse;
		TNT1 A 0
		{
			bSPRITEFLIP = random (0, 1);
		}
		TNT1 A 0 A_Jump (256, "one", "two", "three");
	one:
		CPB1 A -1;
		Stop;
	two:
		CPB2 A -1;
		Stop;
	three:
		CPB2 A -1;
		Stop;
	}
}