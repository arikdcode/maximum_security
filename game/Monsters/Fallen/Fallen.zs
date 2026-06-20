Class Fallen : Actor
{
//$Category Monsters/Custom/Undead
  Default
  {
    Health 200;
    Radius 24;
    Height 48;
    Mass 200;
    Speed 12;
    PainChance 128;
    Obituary "%o got burned by a Fallen.";
    SeeSound "monster/falsit";
    PainSound "monster/falpai";
    DeathSound "monster/faldth";
    ActiveSound "monster/falact";
    Monster;
    +NoGravity
    +Float
  }

  States
  {
  Spawn:
    FALN ABCDB 8 Bright A_Look();
    Loop;
  See:
    FALN A 0 Bright A_Jump(96, "FastSee");
    FALN A 1 Bright A_Playsound("monster/falwng");
    FALN AABBCCDDBB 2 Bright A_Chase();
    Loop;
  FastSee:
    FALN B 2 Bright A_Chase(null, "Missile", CHF_FASTCHASE);
    FALN BBB 2 Bright
    {
      A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
      A_Chase(null, "Missile", CHF_FASTCHASE);
    }
    FALN B 0 Bright A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
    FALN B 0 Bright A_Jump(64, 1);
    Goto See;
    FALN B 2 Bright A_Chase(null, "Missile", CHF_FASTCHASE);
    FALN BBB 2 Bright
    {
      A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
      A_Chase(null, "Missile", CHF_FASTCHASE);
    }
    FALN B 0 Bright A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
    Goto See;
  Missile:
    FALN C 0 Bright A_Jump(128, "Missile2");
    FALN CE 2 Bright A_FaceTarget();
    FALN F 3 Bright A_SpawnProjectile("FallenShot",40,0,0);
    FALN E 2 Bright A_FaceTarget();
    FALN F 3 Bright A_SpawnProjectile("FallenShot",40,0,0);
    FALN E 2 Bright A_FaceTarget();
    FALN F 3 Bright A_SpawnProjectile("FallenShot",40,0,0);
    FALN E 2 Bright A_FaceTarget();
    FALN F 3 Bright A_SpawnProjectile("FallenShot",40,0,0);
    FALN E 2 Bright A_FaceTarget();
    FALN F 3 Bright A_SpawnProjectile("FallenShot",40,0,0);
    FALN E 5 Bright;
    Goto See;
  Missile2:
    FALN CE 2 Bright FaceFastChase();
    FALN F 3 Bright FastChaseFire("FallenShot",40);
    FALN F 0 Bright A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
    FALN CE 2 Bright FaceFastChase();
    FALN F 3 Bright FastChaseFire("FallenShot",40);
    FALN F 0 Bright A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
    FALN C 5 Bright FaceFastChase();
    FALN E 2 Bright FaceFastChase();
    FALN F 3 Bright FastChaseFire("FallenShot",40);
    FALN F 0 Bright A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
    FALN CE 2 Bright FaceFastChase();
    FALN F 3 Bright FastChaseFire("FallenShot",40);
    FALN F 0 Bright A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
    FALN C 2 Bright FaceFastChase();
    FALN E 3 Bright FaceFastChase();
    FALN F 2 Bright FastChaseFire("FallenShot",40);
    FALN F 0 Bright A_SpawnItemEx("FallenFX", 0,0,40, 0,0,0, 0, SXF_CLIENTSIDE);
    FALN E 5 Bright;
    Goto See;
  Pain:
    FALN E 3 Bright;
    FALN E 3 Bright A_Pain();
    FALN E 3 Bright;
    Goto See;
  Death:
    FALN G 5 Bright;
    FALN H 5 Bright A_Scream();
    FALN IJK 5 Bright;
    FALN L 5 Bright A_NoBlocking();
    FALN M -1 A_SetFloorClip();
    Stop;
  Raise:
    FALN M 5 A_UnSetFloorClip();
    FALN LKJIHG 5 Bright;
    Goto See;
  }

  void FaceFastChase()
  {
    A_Chase(null, "Missile", CHF_FASTCHASE);
    A_FaceTarget();
  }

  void FastChaseFire(Class<actor> p, double x)
  {
    A_Chase(null, "Missile", CHF_FASTCHASE);
    A_SpawnProjectile(p, x);
  }
}

Class FallenFX : Actor
{
  Default
  {
    Radius 2;
    Height 2;
    Speed 0;
    RenderStyle "Add";
    Alpha 0.67;
    Projectile;
  }

  States
  {
  Spawn:
    TNT1 A 3 Bright;
    FBFX ABCDE 3 Bright;
    Stop;
  }
}

Class FallenShot : Actor
{
  Default
  {
    Radius 8;
    Height 8;
    Speed 16;
    Damage 2;
    RenderStyle "Add";
    DamageType "Fire";
    Alpha 0.67;
    Seesound "weapons/firmfi";
    DeathSound "weapons/firex5";
    Projectile;
    +ThruGhost
  }

  States
  {
  Spawn:
    BALF AB 2 Bright A_SpawnItemEx("FallenFX", 0,0,0, 0,0,0, 0, SXF_CLIENTSIDE);
    Loop;
  Death:
    BALF CDEF 4 Bright;
    Stop;
  }
}

Class FallenSP : Actor
{
  Default
  {
    Radius 2;
    Height 2;
    Speed 0;
    ReactionTime 60;
    RenderStyle "Normal";
    Projectile;
    -NoGravity
  }

  States
  {
  Spawn:
    FBSP AB 3 Bright A_Countdown();
    Loop;
  Death:
    FBSP CDE 3 Bright;
    Stop;
  }
}
