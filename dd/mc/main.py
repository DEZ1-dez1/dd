"""
Minecraft Clone using Ursina Engine.

A voxel-based sandbox game clone built with Python and Ursina Engine.
"""

from __future__ import annotations

import os
import random

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# Initialize Minecraft app using Ursina Engine
minecraft_app = Ursina()


def resolve_texture_path(*candidates: str) -> str:
  """Return the first existing texture file path among candidates."""
  for path in candidates:
    if os.path.exists(path):
      return path
  return candidates[0]


# Block texture paths (supports both *_2.png and standard *.png names)
BLOCK_TEXTURES: dict[str, str] = {
    'Grass Block': resolve_texture_path(
        'assets/graphical_assets/grass.png',
        'assets/graphical_assets/çimen.jpg',
    ),
    'Sand Block': resolve_texture_path(
        'assets/graphical_assets/sand.png',
    ),
    'Stone Block': resolve_texture_path(
        'assets/graphical_assets/stone_block.png',
    ),
    'Stone Brick': resolve_texture_path(
        'assets/graphical_assets/stone_brick.png',
    ),
    'Wood Plank': resolve_texture_path(
        'assets/graphical_assets/wood_plank.jpg',
    ),
    'Leaves': resolve_texture_path(
        'assets/graphical_assets/leaves.png',
    ),
    'Obsidian': resolve_texture_path(
        'assets/graphical_assets/obsidian.png',
    ),
    'Sponge': resolve_texture_path(
        'assets/graphical_assets/sponge.jpg',
    ),
    'Gold Ore Block': resolve_texture_path(
        'assets/graphical_assets/gold_ore_block_2.png',
        'assets/graphical_assets/gold_ore_block.png',
    ),
    'Diamond Ore Block': resolve_texture_path(
        'assets/graphical_assets/diamond_ore_block_2.png',
        'assets/graphical_assets/diamond_ore_block.png',
    ),
    'Emerald Ore Block': resolve_texture_path(
        'assets/graphical_assets/emerald_ore_block_2.png',
        'assets/graphical_assets/emerald_ore_block.png',
    ),
    'Bedrock': resolve_texture_path(
        'assets/graphical_assets/bedrock.png',
    ),
}

ALL_BLOCK_NAMES: list[str] = list(BLOCK_TEXTURES.keys())

# Load all block textures
grass_block_texture = load_texture(BLOCK_TEXTURES['Grass Block'])
sand_block_texture = load_texture(BLOCK_TEXTURES['Sand Block'])
stone_block_texture = load_texture(BLOCK_TEXTURES['Stone Block'])
stone_brick_texture = load_texture(BLOCK_TEXTURES['Stone Brick'])
wood_plank_texture = load_texture(BLOCK_TEXTURES['Wood Plank'])
leaves_texture = load_texture(BLOCK_TEXTURES['Leaves'])
obsidian_texture = load_texture(BLOCK_TEXTURES['Obsidian'])
sponge_texture = load_texture(BLOCK_TEXTURES['Sponge'])
gold_ore_block_texture = load_texture(BLOCK_TEXTURES['Gold Ore Block'])
diamond_ore_block_texture = load_texture(BLOCK_TEXTURES['Diamond Ore Block'])
emerald_ore_block_texture = load_texture(BLOCK_TEXTURES['Emerald Ore Block'])
bedrock_texture = load_texture(BLOCK_TEXTURES['Bedrock'])

# Sky texture
sky_texture = load_texture('assets/graphical_assets/sky.png')

# Block placing/destroying sound
block_sound = Audio(
    'assets/sound_assets/block_sound.mp3', loop=False, autoplay=False
)

# Player WASD movement sound
player_movement_sound = Audio(
    'assets/sound_assets/player_movement_sound.mp3', loop=True, autoplay=False
)

# Block choice mapping
TEXTURE_MAP: dict[str, Texture] = {
    'Grass Block': grass_block_texture,
    'Sand Block': sand_block_texture,
    'Stone Block': stone_block_texture,
    'Stone Brick': stone_brick_texture,
    'Wood Plank': wood_plank_texture,
    'Leaves': leaves_texture,
    'Obsidian': obsidian_texture,
    'Sponge': sponge_texture,
    'Gold Ore Block': gold_ore_block_texture,
    'Diamond Ore Block': diamond_ore_block_texture,
    'Emerald Ore Block': emerald_ore_block_texture,
    'Bedrock': bedrock_texture,
}

# 9-slot bottom hotbar + 27-slot main inventory (E key)
HOTBAR_SIZE: int = 9
MAIN_INVENTORY_SIZE: int = 27

hotbar_slots: list[str | None] = [
    'Grass Block',
    'Sand Block',
    'Stone Block',
    'Stone Brick',
    'Wood Plank',
    'Leaves',
    'Obsidian',
    'Sponge',
    'Diamond Ore Block',
]
selected_hotbar_index: int = 0
block_choice: str = hotbar_slots[0] or 'Sand Block'

# Populate 27-slot main inventory with all available blocks
main_inventory_slots: list[str | None] = [None] * MAIN_INVENTORY_SIZE
for idx, name in enumerate(ALL_BLOCK_NAMES):
  if idx < MAIN_INVENTORY_SIZE:
    main_inventory_slots[idx] = name

inventory_open: bool = False

dimension: int = 20
stone_layers: int = 10
min_y: int = -(stone_layers + 1)

spectator_mode: bool = False
spectator_speed: float = 12.0

# Grid lookup: (x, y, z) -> Voxel
voxels: dict[tuple[int, int, int], Voxel] = {}

NEIGHBOR_OFFSETS: tuple[tuple[int, int, int], ...] = (
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
    (0, 0, 1),
    (0, 0, -1),
)


def pos_key(pos: Vec3 | tuple[float, float, float]) -> tuple[int, int, int]:
  """Normalize entity position to integer grid key."""
  return (int(round(pos[0])), int(round(pos[1])), int(round(pos[2])))


def is_exposed(coord: tuple[int, int, int]) -> bool:
  """Return True if at least one adjacent face is not occluded by another block."""
  x, y, z = coord
  for dx, dy, dz in NEIGHBOR_OFFSETS:
    if (x + dx, y + dy, z + dz) not in voxels:
      return True
  return False


def refresh_visibility(coord: tuple[int, int, int]) -> None:
  """Update enabled state for a block if it exists."""
  block = voxels.get(coord)
  if block is not None:
    block.enabled = is_exposed(coord)


def refresh_neighbors(coord: tuple[int, int, int]) -> None:
  """Update visibility for a coordinate and all 6 neighboring positions."""
  x, y, z = coord
  refresh_visibility((x, y, z))
  for dx, dy, dz in NEIGHBOR_OFFSETS:
    refresh_visibility((x + dx, y + dy, z + dz))


def pick_underground_texture() -> Texture:
  """Pick stone or random ore texture for underground layers."""
  roll = random.random()
  if roll < 0.05:
    return emerald_ore_block_texture
  if roll < 0.13:
    return diamond_ore_block_texture
  if roll < 0.22:
    return gold_ore_block_texture
  return stone_block_texture


def select_hotbar_slot(index: int) -> None:
  """Select hotbar slot by index (0..8) and update active block."""
  global selected_hotbar_index, block_choice
  if 0 <= index < HOTBAR_SIZE:
    selected_hotbar_index = index
    chosen = hotbar_slots[index]
    if chosen is not None:
      block_choice = chosen
    refresh_inventory_ui()


def on_hotbar_click(index: int) -> None:
  """Handle clicking a hotbar slot."""
  if inventory_open and main_inventory_slots[0] is not None:
    if hotbar_slots[index] is None:
      hotbar_slots[index] = block_choice
  select_hotbar_slot(index)


def on_main_slot_click(index: int) -> None:
  """Select a block from the 27-slot inventory and put it in active hotbar slot."""
  global block_choice
  item = main_inventory_slots[index]
  if item is not None:
    block_choice = item
    hotbar_slots[selected_hotbar_index] = item
    refresh_inventory_ui()


def toggle_main_inventory() -> None:
  """Open or close the 27-slot main inventory with E."""
  global inventory_open
  inventory_open = not inventory_open
  main_inventory_panel.enabled = inventory_open
  mouse.locked = not inventory_open
  minecraft_player.enabled = not inventory_open
  refresh_inventory_ui()


def toggle_spectator_mode() -> None:
  """Toggle noclip/fly spectator mode on or off using I."""
  global spectator_mode
  spectator_mode = not spectator_mode

  if spectator_mode:
    minecraft_player.gravity = 0
    minecraft_player.collider = None
    minecraft_player.speed = 0
    player_hand.enabled = False
    if player_movement_sound.playing:
      player_movement_sound.stop()
  else:
    minecraft_player.gravity = 1
    minecraft_player.collider = 'box'
    minecraft_player.speed = 5
    player_hand.enabled = not inventory_open


def update_spectator_movement() -> None:
  """Move freely in 3D space while in spectator mode."""
  move_vec = Vec3(0, 0, 0)
  forward_xz = Vec3(
      minecraft_player.forward.x, 0, minecraft_player.forward.z
  ).normalized()
  right_xz = Vec3(
      minecraft_player.right.x, 0, minecraft_player.right.z
  ).normalized()

  if held_keys['w']:
    move_vec += forward_xz
  if held_keys['s']:
    move_vec -= forward_xz
  if held_keys['d']:
    move_vec += right_xz
  if held_keys['a']:
    move_vec -= right_xz
  if held_keys['space']:
    move_vec += Vec3(0, 1, 0)
  if held_keys['shift'] or held_keys['c']:
    move_vec -= Vec3(0, 1, 0)

  if move_vec.length() > 0:
    minecraft_player.position += (
        move_vec.normalized() * spectator_speed * time.dt
    )


def input(key: str) -> None:
  """Global keyboard input handler."""
  if key == 'e':
    toggle_main_inventory()
    return

  if inventory_open:
    return

  if key == 'i':
    toggle_spectator_mode()
    return

  if key in '123456789':
    select_hotbar_slot(int(key) - 1)


def update() -> None:
  """
    Update function for block selection, movement audio, and hand movements.

    Called every frame by the Ursina engine.
    """
  if inventory_open:
    if player_movement_sound.playing:
      player_movement_sound.stop()
    return

  if spectator_mode:
    update_spectator_movement()
    return

  # Hand movement on mouse click
  if held_keys['left mouse'] or held_keys['right mouse']:
    player_hand.active()
  else:
    player_hand.passive()

  # WASD movement sound control
  is_moving = (
      held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']
  )
  if is_moving and minecraft_player.grounded:
    if not player_movement_sound.playing:
      player_movement_sound.play()
  else:
    if player_movement_sound.playing:
      player_movement_sound.stop()


class Voxel(Button):
  """
    Voxel class representing a block in the Minecraft world.

    Handles block placement and destruction interactions.
    """

  def __init__(
      self,
      position: tuple[float, float, float] = (0, 0, 0),
      texture: Texture = grass_block_texture,
      use_uv_model: bool = False,
      breakable: bool = True,
  ) -> None:
    if use_uv_model:
      voxel_model = 'block'
      voxel_scale = (0.5, 1.0, 0.5)
      voxel_origin_y = 0
    else:
      voxel_model = 'cube'
      voxel_scale = 1
      voxel_origin_y = 0.5

    super().__init__(
        parent=scene,
        position=position,
        model=voxel_model,
        origin_y=voxel_origin_y,
        texture=texture,
        color=color.white,
        highlight_color=color.light_gray,
        scale=voxel_scale,
    )
    self.breakable = breakable
    self.grid_pos = pos_key(self.position)
    voxels[self.grid_pos] = self

  def input(self, key: str) -> None:
    """
        Handle mouse input for block placement and destruction.

        Args:
            key: The input key/event to handle.
        """
    if inventory_open or not self.hovered:
      return

    if key == 'left mouse down':
      block_sound.play()
      texture = TEXTURE_MAP.get(block_choice, sand_block_texture)
      new_pos = self.position + mouse.normal
      is_grass = texture == grass_block_texture
      new_voxel = Voxel(
          position=new_pos,
          texture=texture,
          use_uv_model=is_grass,
          breakable=True,
      )
      refresh_neighbors(new_voxel.grid_pos)

    elif key == 'right mouse down' and self.breakable:
      block_sound.play()
      removed_pos = self.grid_pos
      voxels.pop(removed_pos, None)
      destroy(self)
      refresh_neighbors(removed_pos)


class Sky(Entity):
  """Sky entity for the Minecraft world."""

  def __init__(self) -> None:
    super().__init__(
        parent=scene,
        model='sphere',
        texture=sky_texture,
        scale=150,
        double_sided=True,
    )


class PlayerHand(Entity):
  """
    Player hand entity for block interaction visualization.

    Handles hand animation when placing/destroying blocks.
    """

  def __init__(self) -> None:
    super().__init__(
        parent=camera.ui,
        model='cube',
        scale=(0.1, 0.99, 0.1),
        texture='assets/graphical_assets/player_arm.png',
        rotation=Vec3(50, 55, -60),
        position=Vec2(0.406, -0.42),
    )

  def active(self) -> None:
    """Move hand to active (clicking) position."""
    self.position = Vec2(0.39, -0.39)

  def passive(self) -> None:
    """Return hand to passive (idle) position."""
    self.position = Vec2(0.406, -0.42)


# Surface grass layer (y=0), 10 stone/ore layers (y=-1 to y=-10), and unbreakable bedrock (y=-11)
for i in range(dimension):
  for j in range(dimension):
    Voxel(
        position=(i, 0, j),
        texture=grass_block_texture,
        use_uv_model=True,
        breakable=True,
    )
    for y in range(1, stone_layers + 1):
      Voxel(
          position=(i, -y, j),
          texture=pick_underground_texture(),
          use_uv_model=False,
          breakable=True,
      )
    Voxel(
        position=(i, min_y, j),
        texture=bedrock_texture,
        use_uv_model=False,
        breakable=False,
    )

# Hide completely enclosed blocks after world generation
for coord, block in voxels.items():
  block.enabled = is_exposed(coord)

# Initialize player with FPP view
minecraft_player = FirstPersonController(position=(10, 2, 10))

# Initialize sky
sky = Sky()

# Initialize player hand
player_hand = PlayerHand()

# --- UI: 9-slot Hotbar + 27-slot Main Inventory (E) ---
hotbar_buttons: list[Button] = []
hotbar_icons: list[Entity] = []

slot_size = 0.068
slot_gap = 0.008
total_hotbar_width = HOTBAR_SIZE * slot_size + (HOTBAR_SIZE - 1) * slot_gap
hotbar_start_x = -total_hotbar_width / 2 + slot_size / 2
hotbar_y = -0.44

for i in range(HOTBAR_SIZE):
  x_pos = hotbar_start_x + i * (slot_size + slot_gap)
  btn = Button(
      parent=camera.ui,
      position=(x_pos, hotbar_y),
      scale=(slot_size, slot_size),
      color=color.rgba(30, 30, 30, 210),
      highlight_color=color.rgba(90, 90, 90, 220),
      text=str(i + 1),
      text_scale=0.6,
      on_click=Func(on_hotbar_click, i),
  )
  icon = Entity(
      parent=btn,
      model='quad',
      scale=0.68,
      z=-0.01,
      color=color.white,
  )
  hotbar_buttons.append(btn)
  hotbar_icons.append(icon)

main_inventory_panel = Entity(
    parent=camera.ui,
    enabled=False,
    position=(0, 0.03),
)

main_inventory_bg = Entity(
    parent=main_inventory_panel,
    model='quad',
    scale=(
        HOTBAR_SIZE * slot_size + (HOTBAR_SIZE + 1) * slot_gap + 0.02,
        3 * slot_size + 4 * slot_gap + 0.02,
    ),
    color=color.rgba(20, 20, 20, 225),
)

main_slot_buttons: list[Button] = []
main_slot_icons: list[Entity] = []

cols = 9
rows = 3
grid_width = cols * slot_size + (cols - 1) * slot_gap
grid_height = rows * slot_size + (rows - 1) * slot_gap
grid_start_x = -grid_width / 2 + slot_size / 2
grid_start_y = grid_height / 2 - slot_size / 2

for idx in range(MAIN_INVENTORY_SIZE):
  row = idx // cols
  col = idx % cols
  x_pos = grid_start_x + col * (slot_size + slot_gap)
  y_pos = grid_start_y - row * (slot_size + slot_gap)
  btn = Button(
      parent=main_inventory_panel,
      position=(x_pos, y_pos, -0.01),
      scale=(slot_size, slot_size),
      color=color.rgba(45, 45, 45, 220),
      highlight_color=color.rgba(120, 120, 120, 240),
      on_click=Func(on_main_slot_click, idx),
  )
  icon = Entity(
      parent=btn,
      model='quad',
      scale=0.68,
      z=-0.01,
      color=color.white,
  )
  main_slot_buttons.append(btn)
  main_slot_icons.append(icon)


def refresh_inventory_ui() -> None:
  """Sync hotbar and 27-slot inventory visuals with current state."""
  for i in range(HOTBAR_SIZE):
    item = hotbar_slots[i]
    is_selected = i == selected_hotbar_index
    hotbar_buttons[i].color = (
        color.rgba(235, 205, 60, 235)
        if is_selected
        else color.rgba(30, 30, 30, 210)
    )
    if item is not None and item in TEXTURE_MAP:
      hotbar_icons[i].enabled = True
      hotbar_icons[i].texture = TEXTURE_MAP[item]
    else:
      hotbar_icons[i].enabled = False

  for idx in range(MAIN_INVENTORY_SIZE):
    item = main_inventory_slots[idx]
    if item is not None and item in TEXTURE_MAP:
      main_slot_icons[idx].enabled = True
      main_slot_icons[idx].texture = TEXTURE_MAP[item]
      main_slot_buttons[idx].color = (
          color.rgba(90, 140, 210, 230)
          if item == block_choice
          else color.rgba(45, 45, 45, 220)
      )
    else:
      main_slot_icons[idx].enabled = False
      main_slot_buttons[idx].color = color.rgba(45, 45, 45, 220)


refresh_inventory_ui()

# Window configuration
window.title = 'Minecraft Clone Using Ursina Engine'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Run Minecraft app
minecraft_app.run()