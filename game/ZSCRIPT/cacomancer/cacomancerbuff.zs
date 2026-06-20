Extend Class Cacomancer
{
	override void Tick()
	{	
		if (!self.bKILLED)
		{
			if(GetAge() % 35 == 0)
			{
				BlockThingsIterator it = BlockThingsIterator.Create(self, arad *1.2);
				while (it.Next())
				{
					let obj = it.thing;
					if (obj.bISMONSTER
						&& obj.health > 0
						&& obj.GetSpecies() != "Cacomancer"
						&& obj.bFRIENDLY == self.bFRIENDLY
						&& !InStateSequence(obj.curstate, obj.ResolveState("Spawn"))
						&& CheckSight(obj)
						&& Distance3D(obj) < arad *1.2)
					{
						obj.GiveInventory("CacomancerAura",1);
					}
				}
			}
			A_SpawnParticle("0000FF",lifetime:35,size:random(3,6),xoff:random(-arad,arad),yoff:random(-arad,arad),zoff:random(-128,128),
				velx:frandom(-2.4,2.4),vely:frandom(-2.4,2.4),velz:frandom(-2.4,2.4),startalphaf:0.5,fadestepf:-1,sizestep:0.25);
			A_SpawnParticle("1000FF",lifetime:35,size:random(3,6),xoff:random(-arad,arad),yoff:random(-arad,arad),zoff:random(-128,128),
				velx:frandom(-2.4,2.4),vely:frandom(-2.4,2.4),velz:frandom(-2.4,2.4),startalphaf:0.5,fadestepf:-1,sizestep:0.25);
			A_SpawnParticle("2000FF",lifetime:35,size:random(3,6),xoff:random(-arad,arad),yoff:random(-arad,arad),zoff:random(-128,128),
				velx:frandom(-2.4,2.4),vely:frandom(-2.4,2.4),velz:frandom(-2.4,2.4),startalphaf:0.5,fadestepf:-1,sizestep:0.25);
			A_SpawnParticle("3000FF",lifetime:35,size:random(3,6),xoff:random(-arad,arad),yoff:random(-arad,arad),zoff:random(-128,128),
				velx:frandom(-2.4,2.4),vely:frandom(-2.4,2.4),velz:frandom(-2.4,2.4),startalphaf:0.5,fadestepf:-1,sizestep:0.25);
		}
		super.Tick();
	}
}
//============================= Aura ===========================================
class CacomancerAura : PowerProtection
{
	Default
	{
		DamageFactor "Normal", 0.667;
		Inventory.MaxAmount 1;
		Powerup.Duration -2;
	}
	
	override void InitEffect()
	{
		super.InitEffect();
		if (owner)
		{
			owner.bNOPAIN = true;
			owner.A_AttachLight("CCDAL",DynamicLight.PulseLight,"3030FF",owner.radius*1.25,owner.radius*1.5,
				flags:DYNAMICLIGHT.LF_NOSHADOWMAP,
				ofs:(0,0,owner.height/2),param:3.5);
		}
	}
	
	override void Tick()
	{	
		if (owner)
		{
			if (GetAge() % 7 == 0)
			{
				owner.A_DamageSelf(-2); //heal 10 hp/s
				if (!owner.CountInv("CacomancerBuff"))
				{
					CacomancerAuraParticle("0000C0", owner.pos, owner.radius, owner.height);
					CacomancerAuraParticle("4020C0", owner.pos, owner.radius, owner.height);
					CacomancerAuraParticle("0000FF", owner.pos, owner.radius, owner.height);
					CacomancerAuraParticle("4020FF", owner.pos, owner.radius, owner.height);
				}
			}
		}
		super.Tick();
	}
	
	void CacomancerAuraParticle(color col, vector3 ps, double rd, double ht)
	{
		A_SpawnParticle(col,
		flags: SPF_FULLBRIGHT,
		lifetime:random(5,9),
		size:random(3,6),
		xoff:ps.x+random(-rd,rd),
		yoff:ps.y+random(-rd,rd),
		zoff:ps.z+random(10,ht),
		velx:random(-1,1),
		vely:random(-1,1),
		velz:random(2,3),
		startalphaf:0.7,fadestepf:-1);
	}
	
	override void EndEffect()
	{
		if (owner) //reset to defaults
		{	
			owner.speed = owner.default.speed;
			owner.bMISSILEMORE = owner.default.bMISSILEMORE;
			owner.bMISSILEEVENMORE = owner.default.bMISSILEEVENMORE;
			owner.bNOPAIN = owner.default.bNOPAIN;
			owner.A_RemoveLight("CCDAL");
			owner.A_RemoveLight("CCDBL");
			owner.TakeInventory("CacomancerBuff",1);
		}
		super.EndEffect();
	}
}

//============================ Buff ============================================
class CacomancerBuff : PowerDamage 
{
	Default
	{
		DamageFactor "Normal", 1.333;
		Inventory.MaxAmount 1;
		Powerup.Duration -30;
	}
	
	override void InitEffect()
	{
		super.InitEffect();
		if (owner)
		{
			owner.PlaySpawnSound(owner);
			owner.speed = owner.default.speed * 1.333; //speed up movement
			owner.bMISSILEEVENMORE = true;
			owner.A_AttachLight("CCDBL",DynamicLight.PulseLight,"CC00CC",owner.radius*1.5,owner.radius*1.8,
				flags:DYNAMICLIGHT.LF_NOSHADOWMAP,
				ofs:(0,0,owner.height/2),param:1);
		}
	}
	
	override void Tick()
	{	
		if (owner)
		{
			if (owner.tics > 2) owner.tics -= 1; //speed up animations
			if (GetAge() % 7 == 0) 
			{
				CacomancerBuffParticle("FF00FF", owner.pos, owner.radius, owner.height);
				CacomancerBuffParticle("C000FF", owner.pos, owner.radius, owner.height);
				CacomancerBuffParticle("8000FF", owner.pos, owner.radius, owner.height);
				CacomancerBuffParticle("4000FF", owner.pos, owner.radius, owner.height);
			}
		}
		super.Tick();
	}
	
	void CacomancerBuffParticle(color col, vector3 ps, double rd, double ht)
	{
		A_SpawnParticle(col,
		flags: SPF_FULLBRIGHT,
		lifetime:random(7,14),
		size:random(3,6),
		xoff:ps.x+random(-rd,rd),
		yoff:ps.y+random(-rd,rd),
		zoff:ps.z+random(10,ht),
		velx:random(-3,2),
		vely:random(-3,2),
		velz:random(-3,3),
		startalphaf:0.7,fadestepf:-1);
	}
}