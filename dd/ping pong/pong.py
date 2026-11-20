from ursina import *

app = Ursina()

# Klasik siyah tema ve 2D kamera ayarları
window.title = "Ursina Ping Pong - Klasik Tema"
window.borderless = False
window.fullscreen = False
window.color = color.black
camera.orthographic = True
camera.fov = 14

# Saha sınırları
TOP_LIMIT = 6.0
BOTTOM_LIMIT = -6.0
LEFT_LIMIT = -10.5
RIGHT_LIMIT = 10.5

# Orta çizgi (beyaz kesikli çizgi)
for y in range(-5, 6, 2):
    Entity(
        model="quad",
        color=color.rgba(255, 255, 255, 90),
        scale=(0.12, 0.9),
        position=(0, y, 0.2),
    )

# Üst ve alt sınır çizgileri
Entity(
    model="quad",
    color=color.white,
    scale=(21.5, 0.16),
    position=(0, TOP_LIMIT + 0.08, 0.1),
)
Entity(
    model="quad",
    color=color.white,
    scale=(21.5, 0.16),
    position=(0, BOTTOM_LIMIT - 0.08, 0.1),
)

# Beyaz oyuncular (raketler)
paddle_left = Entity(
    model="quad",
    color=color.white,
    scale=(0.4, 2.4),
    position=(-9, 0, 0.2),
    collider="box",
)

paddle_right = Entity(
    model="quad",
    color=color.white,
    scale=(0.4, 2.4),
    position=(9, 0, 0.2),
    collider="box",
)

# Beyaz top (her kurulumda net görünmesi için quad + yüksek z sırası)
ball = Entity(
    model="quad",
    color=color.white,
    scale=(0.45, 0.45),
    position=(0, 0, 0.3),
    collider="box",
)

# Oyun değişkenleri
PADDLE_SPEED = 9.0
INITIAL_BALL_SPEED = 8.5
MAX_BALL_SPEED = 18.0
ball_speed = INITIAL_BALL_SPEED
ball_velocity = Vec2(random.choice([-1, 1]), random.uniform(-0.5, 0.5)).normalized()

score_left = 0
score_right = 0
ai_right = False

# Skor ve bilgi metinleri
score_text = Text(
    text=f"{score_left}   -   {score_right}",
    scale=2.5,
    origin=(0, 0),
    position=(0, 5.2, 0.4),
    color=color.white,
)

mode_text = Text(
    text="Klasik Siyah/Beyaz | 2 Oyuncu (W/S & Oklar) | [B] Bot | [R] Sıfırla",
    scale=1.05,
    origin=(0, 0),
    position=(0, -6.55, 0.4),
    color=color.light_gray,
)


def reset_ball(direction_x=None):
    global ball_speed, ball_velocity
    ball.position = (0, 0, 0.3)
    ball_speed = INITIAL_BALL_SPEED
    dx = direction_x if direction_x is not None else random.choice([-1, 1])
    dy = random.uniform(-0.6, 0.6)
    ball_velocity = Vec2(dx, dy).normalized()


def reset_game():
    global score_left, score_right
    score_left = 0
    score_right = 0
    paddle_left.y = 0
    paddle_right.y = 0
    score_text.text = f"{score_left}   -   {score_right}"
    reset_ball()


def input(key):
    global ai_right
    if key == "b":
        ai_right = not ai_right
        mode_str = "Tek Oyuncu (Sağ: Bot)" if ai_right else "2 Oyuncu (W/S & Oklar)"
        mode_text.text = f"Klasik Siyah/Beyaz | {mode_str} | [B] Bot | [R] Sıfırla"
    elif key == "r":
        reset_game()


def update():
    global ball_speed, ball_velocity, score_left, score_right

    dt = time.dt

    # Sol raket
    if held_keys["w"]:
        paddle_left.y += PADDLE_SPEED * dt
    if held_keys["s"]:
        paddle_left.y -= PADDLE_SPEED * dt

    # Sağ raket
    if ai_right:
        diff = ball.y - paddle_right.y
        if abs(diff) > 0.15:
            paddle_right.y += clamp(diff * 5.5, -PADDLE_SPEED * 0.85, PADDLE_SPEED * 0.85) * dt
    else:
        if held_keys["up arrow"]:
            paddle_right.y += PADDLE_SPEED * dt
        if held_keys["down arrow"]:
            paddle_right.y -= PADDLE_SPEED * dt

    # Raket sınırları
    half_paddle = paddle_left.scale_y / 2
    paddle_left.y = clamp(paddle_left.y, BOTTOM_LIMIT + half_paddle, TOP_LIMIT - half_paddle)
    paddle_right.y = clamp(paddle_right.y, BOTTOM_LIMIT + half_paddle, TOP_LIMIT - half_paddle)

    # Top hareketi
    ball.x += ball_velocity.x * ball_speed * dt
    ball.y += ball_velocity.y * ball_speed * dt

    # Üst ve alt duvar
    half_ball = ball.scale_y / 2
    if ball.y + half_ball >= TOP_LIMIT:
        ball.y = TOP_LIMIT - half_ball
        ball_velocity.y = -abs(ball_velocity.y)
    elif ball.y - half_ball <= BOTTOM_LIMIT:
        ball.y = BOTTOM_LIMIT + half_ball
        ball_velocity.y = abs(ball_velocity.y)

    # Sol raket çarpışması
    hit_info_left = ball.intersects(paddle_left)
    if hit_info_left.hit and ball_velocity.x < 0:
        rel_y = clamp((ball.y - paddle_left.y) / half_paddle, -1, 1)
        ball_velocity = Vec2(1, rel_y * 0.85).normalized()
        ball_speed = min(ball_speed * 1.06, MAX_BALL_SPEED)

    # Sağ raket çarpışması
    hit_info_right = ball.intersects(paddle_right)
    if hit_info_right.hit and ball_velocity.x > 0:
        rel_y = clamp((ball.y - paddle_right.y) / half_paddle, -1, 1)
        ball_velocity = Vec2(-1, rel_y * 0.85).normalized()
        ball_speed = min(ball_speed * 1.06, MAX_BALL_SPEED)

    # Skor kontrolü
    if ball.x < LEFT_LIMIT:
        score_right += 1
        score_text.text = f"{score_left}   -   {score_right}"
        reset_ball(direction_x=-1)
    elif ball.x > RIGHT_LIMIT:
        score_left += 1
        score_text.text = f"{score_left}   -   {score_right}"
        reset_ball(direction_x=1)


app.run()