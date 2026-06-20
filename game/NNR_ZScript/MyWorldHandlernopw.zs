class MyWorldHandler : EventHandler
{
    Array<Actor> HelgaList; // automatically allocated by ZScript

    // PostBeginPlay no longer needs to initialize the array
    override void PostBeginPlay()
    {
        super.PostBeginPlay();
        // no need to do anything
    }

    void GiveHelga(Actor activator)
    {
        if (!activator || !activator.player) return;

        let pnum = activator.PlayerNumber();
        if (pnum < 0 || pnum >= MAXPLAYERS) return;

        let pl = players[pnum].mo;
        if (!pl) return;

        let helga = pl.Spawn("NNR_FriendHelga", pl.pos, ALLOW_REPLACE);
        if (!helga) return;

        helga.Master = pl;
        helga.Translation = pl.Translation;
        helga.A_FaceMaster();

        HelgaList.Push(helga);

        Console.Printf("Spawned Helga for player %d", pnum);
    }

    void RemoveHelgas()
    {
        for (int i = 0; i < HelgaList.Size(); i++)
        {
            let h = HelgaList[i];
            if (h && !h.bDestroyed)
                h.Destroy();
        }
        HelgaList.Clear();

        Console.Printf("All Helgas destroyed.");
    }
}