Class Ghoul : Actor
{
//$Category Monsters/Custom/Undead
  Default
  {
    Health 200;
    PainChance 24;
    Speed 9;
    Radius 24;
    Height 56;
    Mass 320;
    BloodColor "20 60 20";
    Obituary "A Ghoul poisoned %o with it's toxic projectiles.";
    HitObituary "%o was beaten to death by a ghoul.";
    SeeSound "ghoul/Zombie";
    PainSound "monster/ghlpai";
    DeathSound "monster/ghldth";
    ActiveSound "monster/ghlact";
    MONSTER;
    +FLOORCLIP
    +DONTHARMCLASS
  }

  States
  {
  Spawn:
    GHOU AB 10 A_Look();
    Loop;
  See:
    GHOU AABBCCDD 2 A_Chase();
    Loop;
  Melee:
    GHOU E 0 A_Jump(128, "Melee2");
    GHOU E 6 A_FaceTarget();
    GHOU F 0 A_PlaySound("monster/ghlswg");
    GHOU F 6 A_FaceTarget();
    GHOU G 5 A_CustomMeleeAttack(4*random(1,8), "monster/ghlhit");
    Goto See;
  Melee2:
    GHOU R 6 A_FaceTarget();
    GHOU S 0 A_PlaySound("monster/ghlswg");
    GHOU S 6 A_FaceTarget();
    GHOU T 5 A_CustomMeleeAttack(4*random(1,8), "monster/ghlhit");
    Goto See;
  Missile:
    GHOU Q 10 A_FaceTarget();
    GHOU Q 8
    {
      A_SpawnProjectile("ToxinShot",44,-16,0,0,0);
      A_SpawnProjectile("ToxinShot",44, 16,0,0,0);
    }
    Goto See;
  Pain:
    GHOU H 2;
    GHOU H 2 A_Pain();
    Goto See;
  Death:
    GHOU I 5;
    GHOU J 0 A_SpawnProjectile("ToxinCloud",40,0,0,0,0);
    GHOU J 5 A_Scream();
    GHOU K 5;
    GHOU L 5 A_NoBlocking();
    GHOU M 5;
    GHOU N 5;
    GHOU O 5;
    GHOU P -1;
    Stop;
  Raise:
    GHOU PONMLKJI 5;
    Goto See;
  }
}

Class ToxinShot : Actor
{
  Default
  {
    Radius 5;
    Height 5;
    Speed 15;
    Damage 2;
    PoisonDamage 16;
    RENDERSTYLE "ADD";
    ALPHA 0.80;
    Seesound "weapons/skulfi";
    DeathSound "weapons/bloodx";
    PROJECTILE;
    +THRUGHOST
    +FLOATBOB
  }

  States
  {
  Spawn:
    GHFX A 1 Bright A_SpawnItemEx("GhoulBarbtrail", 0,0,0, 0,0,0, 0, SXF_CLIENTSIDE);
    GHFX A 1 Bright A_CStaffMissileSlither();
    GHFX B 1 Bright A_SpawnItemEx("GhoulBarbtrail", 0,0,0, 0,0,0, 0, SXF_CLIENTSIDE);
    GHFX B 1 Bright A_CStaffMissileSlither();
    loop;
  Death:
    GHFX CDEF 4 Bright;
    stop;
  }
}

Class ToxinCloud : Actor
{
  Default
  {
    Radius 0;
    Height 48;
    RENDERSTYLE "translucent";
    ReactionTime 20;
    ALPHA 0.67;
    Seesound "weapons/poof1";
    MONSTER;
    -SOLID
    -SHOOTABLE
    -ACTIVATEMCROSS
    -COUNTKILL
    +NOTELEPORT
    +THRUGHOST
    +DROPOFF
    //+LOWGRAVITY
	Gravity 0.2;
    +NODAMAGETHRUST
  }

  States
  {
  Spawn:
    GGAS ABCDEFGFD 5 A_Explode(5, 42);
    GGAS A 0 A_Countdown;
    goto Spawn+2;
  Death:
    GGAS C 5 A_FadeOut(0.10);
    GGAS C 0 A_Explode(5, 42);
    GGAS D 5 A_FadeOut(0.10);
    GGAS C 0 A_Explode(5, 42);
    GGAS E 5 A_FadeOut(0.10);
    GGAS C 0 A_Explode(5, 42);
    GGAS F 5 A_FadeOut(0.10);
    GGAS C 0 A_Explode(5, 42);
    GGAS G 5 A_FadeOut(0.10);
    GGAS C 0 A_Explode(5, 42);
    GGAS F 5 A_FadeOut(0.10);
    GGAS C 0 A_Explode(5, 42);
    GGAS E 5 A_FadeOut(0.10);
    GGAS C 0 A_Explode(5, 42);
    GGAS D 5 A_FadeOut(0.10);
    loop;
  }
}

Class GhoulBarbtrail : Actor
{
  Default
  {
    Radius 0;
    Height 1;
    PROJECTILE;
    RENDERSTYLE "ADD";
    ALPHA 0.75;
  }

  States
  {
  Spawn:
    TNT1 A 1 Bright;
    GHFX GHIJKLM 2 Bright;
    Stop;
  }
}

