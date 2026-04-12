class BaseWeapon:
    """Abstract base for all weapons.

    Lifecycle per key-press:
      on_press(owner)                       — called once on KEYDOWN
      update(owner, keys_pressed, players)  — called every frame while shoot_block is True
                                              returns (owner_id | None, pygame.Rect | None)
      on_release(owner)                     — called once on KEYUP
      draw(win, owner)                      — called every frame to render weapon overlays
    """

    def on_press(self, owner):
        """Called once when the shoot key is pressed."""
        pass

    def update(self, owner, keys_pressed, players):
        """Called every frame.  Returns (id | None, Rect | None) for the shot visualisation."""
        return (None, None)

    def on_release(self, owner):
        """Called once when the shoot key is released."""
        pass

    def draw(self, win, owner):
        """Draw any weapon-specific overlay (cone arcs, charge bars, etc.)."""
        pass
