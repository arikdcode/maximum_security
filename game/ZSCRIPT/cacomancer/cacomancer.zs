class Cacomancer : Actor
{
	int arad;
	override void PostBeginPlay()
	{
		arad = 667;	// Aura radius
		Super.PostBeginPlay();
	}
	
	Default
	{
		//$Category Monsters
		//$Title "Cacomancer"
		Health 280;
		Radius 20;
		Height 60;
		Mass 150;
		Speed 8;
		PainChance 200;
		Monster;
		Scale 0.667;
		//+MISSILEMORE;
		MissileChanceMult 0.5;
		+DONTHARMCLASS;
		+NOGRAVITY;
		+FLOAT;
		+AVOIDMELEE;
		//+NOINFIGHTING;
		+NOTARGET;
		PainSound "Cacomancer/pain";
		DeathSound "Cacomancer/death";
		ActiveSound "Cacomancer/active";
		Obituary "%o was killed by a Cacomancer.";
	}
	States
	{
	Spawn:
		VCCM A 2 A_Look;
		Loop;
	See:
		TNT1 A 0 A_Startsound("Cacomancer/see",13100);
	Roam:
		TNT1 A 0
		{
			vel *= 0.5;
			if (target && target.bISMONSTER)
			{
				target = NULL;
				A_LookEx(LOF_NOJUMP); //Aquire new target
			}
			if (!random(0,15)) SetStateLabel("Dodge");
		}
		VCCM A 2
		{
			if (target && Distance3D(target) < 200)
			{
				A_FaceTarget();
				A_Recoil(random(5,10));
				if (!random(0,1)) SetStateLabel("Dodge");
				else SetStateLabel("MissileBall");
			}
			else A_Chase();
		}
		Loop;
	Missile:
		VCCM A 10
		{
			BlockThingsIterator it = BlockThingsIterator.Create(self, arad);
			while (it.Next())
			{
				let obj = it.thing;
				if (obj.bISMONSTER
					&& obj.CanRaise()
					&& CheckSight(obj)
					&& Distance3D(obj) < arad)
				{
					target = obj;
					A_Startsound("Cacomancer/heal");
					SetStateLabel("MissileHeal");
				}
				if (obj.bISMONSTER
					&& !obj.bKILLED
					&& !obj.CountInv("CacomancerBuff")
					&& obj.GetSpecies() != "Cacomancer"
					&& obj.bFRIENDLY == self.bFRIENDLY
					&& !InStateSequence(obj.curstate, obj.ResolveState("Spawn"))
					&& CheckSight(obj)
					&& Distance3D(obj) < arad)
				{
					target = obj;
					A_Startsound("Cacomancer/buff");
					SetStateLabel("MissileBuff");
				}
			}
		}
	MissileBall:
		VCCM BC random(3,5) 
		{
			A_FaceTarget();
			A_Recoil(random(0,2));
		}
		VCCM D 10 Bright A_SpawnProjectile("CacomancerBall",32);
		VCCM CB random(3,5);
		Goto Roam;
	MissileHeal:
		VCCM OOO 5 Bright
		{
			A_FaceTarget();
			A_Recoil(random(-1,0));
		}
		VCCM PPPPPPPPPP 1 Bright
		{
			if (target)
			{
				A_FaceTarget();
				A_SpawnProjectile("CacomancerHealMissile",51);
			}
		}
		VCCM OOOO 5 Bright;
		Goto Roam;
	MissileBuff:
		VCCM MMM 5 Bright
		{
			A_FaceTarget();
			A_Recoil(random(-1,0));
		}
		VCCM NNNNNNNNNN 1 Bright
		{
			if (target)
			{
				A_FaceTarget();
				A_SpawnProjectile("CacomancerBuffMissile",51);
			}
		}
		VCCM MMMM 5 Bright;
		Goto Roam;
	Dodge:
		TNT1 A 0
		{
			A_FaceTarget();
			if (target)
			{
				double ang = angleto(target);
				ThrustThing(ang*256/360+randompick(64,192),random(2,4),0,0);
				ThrustThingZ(0, random(0,10), 0, 1);
				ThrustThingZ(0, random(0,5), 1, 1);
			}	
		}
		VCCM AAAAAAAAAA 2
		{
			A_FaceTarget();
			vel *= 0.9;
			A_Chase();
		}
		Goto Roam;
	Pain:
		VCCM E 5;
		VCCM F 10 A_Pain;
		Goto Roam;
	Death:
		VCCM F 5;
		VCCM G 5 A_Scream;
		VCCM H 5;
		VCCM I 5;
		VCCM J 5 A_NoBlocking;
		VCCM K 5;
		VCCM L 9;
		VCCM Q 3;
		VCCM R 3;
		VCCM Q 3;
		VCCM L 9;
		VCCM Q 3;
		VCCM R 3;
		VCCM S -1;
		Stop;
	Raise:
		Stop;
	}
}

class CacomancerHealMissile : Actor
{
	Default
	{
		Radius 6;
		Height 8;
		Speed 15;
		Damage 0;
		Scale 0.5;
		Projectile;
		+SEEKERMISSILE;
		+ROLLSPRITE;
		Renderstyle "Add";
		Alpha 1.0;
		Translation "0:255=%[0.4,0.1,0.1]:[1.0,0.3,0.3]";
	}
	States
	{
	Spawn:
		TNT1 A 0 Nodelay 
		{	
			A_SetRoll(random(0, 359));
		}
		VCMP BCDDEEFFGGGHHH 2 Bright
		{
			scale.y -= 0.01667;
			roll += 20;
			A_SeekerMissile(5, 45);
			A_CheckForResurrection();
		}
		VCMP GGFFEEDCBA 2 Bright
		{
			A_Fadeout(0.1);
			roll += 20;
			A_CheckForResurrection();
		}
		Loop;
	Death:
		#### # 1 Bright
		{
			scale.x -= 0.01;
			scale.y -= 0.01;
			A_Fadeout(0.1);
			A_CheckForResurrection();
		}
		Loop;
	Heal:
		#### # 2 Bright A_Fadeout(0.1);
		Loop;
	}
	
	override int SpecialMissileHit(Actor victim)
	{
		if (target && victim.bISMONSTER && victim.health > 0 && victim.GetSpecies() != "Cacomancer")
		{
			victim.bFRIENDLY = target.bFRIENDLY; //makes sure the revived monster is on the Cacomancer's side
		}
		return -1;
	}
}

class CacomancerBuffMissile : Actor
{
	Default
	{
		Radius 6;
		Height 8;
		Speed 15;
		Damage 0;
		Scale 0.5;
		Projectile;
		+SEEKERMISSILE;
		+ROLLSPRITE;
		Renderstyle "Add";
		Alpha 1.0;
	}
	States
	{
	Spawn:
		TNT1 A 0 Nodelay A_SetRoll(random(0, 359));
		VCMP BCDDEEFFFGGGHHH 2 Bright
		{
			scale.y -= 0.01667;
			roll += 20;
			A_SeekerMissile(5, 45);
		}
		VCMP GGFFEEDCBA 2 Bright
		{
			roll += 20;
			A_Fadeout(0.1);
		}
		Loop;
	Death:
		#### # 1 Bright
		{
			scale.x -= 0.01;
			scale.y -= 0.01;
			A_Fadeout(0.1);
		}
		Loop;
	}
	
	override int SpecialMissileHit(Actor victim)
	{
		if (victim.bISMONSTER && victim.health > 0 && victim.GetSpecies() != "Cacomancer")
		{
			victim.GiveInventory("CacomancerBuff",1);
		}
		return -1;
	}
}

class CacomancerBall : CacodemonBall
{
	Default
	{
 		Radius 5;
		Height 7;
		Speed 10;
		Damage 4;
		Scale 0.8;
		+ROLLSPRITE;
		SeeSound "Cacomancer/attack";
	}
	States
	{
	Spawn:
 		VCMB AB 4 Bright
		{
			A_SetRoll(random(0, 359));
		}
		Loop;
	Death:
		VCMB CDE 6 Bright;
		Stop;
	}
}