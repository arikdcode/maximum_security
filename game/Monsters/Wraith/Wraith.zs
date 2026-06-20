Class DEWraith : Actor
{
  Default
  {
    Health 50;
    Radius 16;
    Height 32;
    Mass 50;
    Speed 10;
    Damage 2;
    RENDERSTYLE "ADD";
    Obituary "A wraith had it's way with %o.";
    HitObituary "%o got bitten by a wraith too many times.";
    ALPHA 0.67;
    PAINCHANCE 64;
    AttackSound "monster/sprsit";
    PainSound "archvile/pain";
    DeathSound "monster/sprdth";
    MONSTER;
    +DONTGIB
    +NOTARGET
    +NOGRAVITY
    +FLOAT
    +DONTFALL
    +DONTHARMCLASS
    +THRUGHOST
  }

  States
  {
  Spawn:
    WRAI AB 10 A_Look();
    Loop;
  See:
    WRAI AABB 3 A_VileChase();
    Loop;
  Missile:
    WRAI A 10 A_FaceTarget();
    WRAI B 4 A_SkullAttack();
    WRAI AB 4;
    Goto Missile+2;
  Melee:
    WRAI A 5 A_FaceTarget();
    WRAI B 5 A_CustomMeleeAttack(Random(1,8), "monster/spratk");
    Goto See;
  Heal:
    WRAI AB 3;
    WRAI B 0 A_Die();
    Goto Death;
  Pain:
    WRAI A 3;
    WRAI A 3 A_Pain();
    Goto See;
  Death:
    WRAI E 4 A_Noblocking();
    WRAI F 5 A_Scream();
    WRAI GHIJ 4;
    Stop;
  }
}

Class DEWraithThrustable : Actor
{
  Default
  {
    Health 50;
    Radius 16;
    Height 32;
    Mass 50;
    Speed 10;
    Damage 2;
    RENDERSTYLE "ADD";
    Obituary "A wraith had it's way with %o.";
    HitObituary "%o got bitten by a wraith too many times.";
    ALPHA 0.67;
    PAINCHANCE 64;
    AttackSound "monster/sprsit";
    PainSound "archvile/pain";
    DeathSound "monster/sprdth";
    MONSTER;
    +DONTGIB
    +NOTARGET
    //+NOGRAVITY
    +FLOAT
    +DONTFALL
    +DONTHARMCLASS
    //+THRUGHOST
	+WINDTHRUST
  }

  States
  {
  Spawn:
    WRAI AB 10 A_Look();
    Loop;
  See:
    WRAI AABB 3 A_VileChase();
    Loop;
  Missile:
    WRAI A 10 A_FaceTarget();
    WRAI B 4 A_SkullAttack();
    WRAI AB 4;
    Goto Missile+2;
  Melee:
    WRAI A 5 A_FaceTarget();
    WRAI B 5 A_CustomMeleeAttack(Random(1,8), "monster/spratk");
    Goto See;
  Heal:
    WRAI AB 3;
    WRAI B 0 A_Die();
    Goto Death;
  Pain:
    WRAI A 3;
    WRAI A 3 A_Pain();
    Goto See;
  Death:
    WRAI E 4 A_Noblocking();
    WRAI F 5 A_Scream();
    WRAI GHIJ 4;
    Stop;
  }
}
