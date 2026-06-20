class MyWorldHandler : EventHandler
{
    Actor Helga; // instance variable

    void GiveHelgaInstance(Actor activator)
    {
        if (!activator || !activator.player) return;
        let pl = players[activator.PlayerNumber()].mo;
        if (!pl) return;

        if (Helga && !Helga.bDestroyed) return;

        Helga = pl.Spawn("NNR_FriendHelga", pl.pos, ALLOW_REPLACE);
        if (!Helga) return;

        Helga.Master = pl;
        Helga.Translation = pl.Translation;
        Helga.A_FaceMaster();
		
		//Helga.SetThingId() = 1234;

        Console.Printf("Helga has joined your party!");
    }

    void RemoveHelgaInstance()
    {
        if (Helga && !Helga.bDestroyed)
        {
            Helga.Destroy();
            Helga = null;
            Console.Printf("Helga has left.");
        }
    }

    // ------------------------------
    // Static functions called from ACS
    // ------------------------------
    static void GiveHelga(Actor activator)
    {
        // Find the handler instance in the map
        MyWorldHandler handler = MyWorldHandler(EventHandler.Find("MyWorldHandler"));
        if (handler) handler.GiveHelgaInstance(activator);
    }

    static void RemoveHelga()
    {
        MyWorldHandler handler = MyWorldHandler(EventHandler.Find("MyWorldHandler"));
        if (handler) handler.RemoveHelgaInstance();
    }
}