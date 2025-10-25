"""
Directional / Spatial Stroop (Spatial Attention) game using pygame.

Rules implemented:
 - Each trial shows a WORD: "LEFT" or "RIGHT".
 - A DISTRACTOR ARROW is drawn on screen and may point left or right (congruent or incongruent).
 - Player must respond according to the WORD (text), NOT the arrow.
 - Respond by clicking the on-screen LEFT or RIGHT buttons or by pressing Left/Right arrow keys.
 - Correctness is judged by the WORD.
 - Shows feedback (Correct / Wrong), reaction time, score, and a progress bar.
 - Configurable number of trials, durations, and difficulty.

Author: ChatGPT (GPT-5 Thinking mini)
"""

import pygame
import random
import time
import sys

# -------------------- Config --------------------
FPS = 60
SCREEN_SIZE = (1000, 650)
TRIALS = 40                    # number of trials in a session
STIMULUS_DURATION = 1.2        # seconds stimulus remains on screen
FEEDBACK_DURATION = 0.6        # seconds feedback shown (correct/wrong)
FIXATION_DURATION = 0.5        # seconds fixation cross
SHOW_ARROW = True              # whether to show distractor arrow (True = show)
CONGRUENCY_PROPORTION = 0.5    # fraction of congruent trials (0.0 - 1.0)
FONT_NAME = None               # None -> default system font; set to "Arial" etc.

# Colors (RGB)
BG_TOP = (16, 24, 40)
BG_BOTTOM = (12, 78, 120)
CARD_COLOR = (240, 248, 255)
TEXT_COLOR = (20, 20, 30)
ACCENT = (255, 180, 85)
CORRECT_GREEN = (20, 160, 80)
WRONG_RED = (220, 60, 60)
BUTTON_COLOR = (30, 40, 60)
BUTTON_HOVER = (50, 70, 100)

# ------------------------------------------------

pygame.init()
screen = pygame.display.set_mode(SCREEN_SIZE)
pygame.display.set_caption("Directional / Spatial Stroop — Spatial Attention")
clock = pygame.time.Clock()

# Fonts
def font(size, bold=False):
    return pygame.font.SysFont(FONT_NAME, size, bold=bold)

TITLE_FONT = font(36, True)
WORD_FONT = font(84, True)
SMALL_FONT = font(22)
BUTTON_FONT = font(28, True)

# Button class for clicking
class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.hot = False

    def draw(self, surf):
        color = BUTTON_HOVER if self.hot else BUTTON_COLOR
        pygame.draw.rect(surf, color, self.rect, border_radius=12)
        # inner card
        inner = self.rect.inflate(-6, -6)
        pygame.draw.rect(surf, CARD_COLOR, inner, border_radius=10)
        txt = BUTTON_FONT.render(self.text, True, TEXT_COLOR)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def update(self, mpos):
        self.hot = self.rect.collidepoint(mpos)

    def clicked(self, mpos):
        return self.rect.collidepoint(mpos)

# Utility to draw gradient background
def draw_gradient(surf, top_color, bottom_color):
    w, h = surf.get_size()
    for y in range(h):
        t = y / (h - 1)
        color = (
            int(top_color[0] * (1 - t) + bottom_color[0] * t),
            int(top_color[1] * (1 - t) + bottom_color[1] * t),
            int(top_color[2] * (1 - t) + bottom_color[2] * t),
        )
        pygame.draw.line(surf, color, (0, y), (w, y))

# Draw arrow as polygon
def draw_arrow(surface, center, size, direction, color=TEXT_COLOR):
    # direction: "LEFT" or "RIGHT"
    cx, cy = center
    w = size * 1.6
    h = size
    if direction == "RIGHT":
        points = [
            (cx - w/2, cy - h/2),
            (cx, cy - h/2),
            (cx + w/2, cy),
            (cx, cy + h/2),
            (cx - w/2, cy + h/2),
            (cx - w/2 + h*0.2, cy)
        ]
    else:  # LEFT
        points = [
            (cx + w/2, cy - h/2),
            (cx, cy - h/2),
            (cx - w/2, cy),
            (cx, cy + h/2),
            (cx + w/2, cy + h/2),
            (cx + w/2 - h*0.2, cy)
        ]
    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, (0,0,0,40), points, 2)

# Build trials
def make_trials(n, congruency_prop=0.5):
    trials = []
    n_congruent = int(round(n * congruency_prop))
    n_incongruent = n - n_congruent
    for _ in range(n_congruent):
        word = random.choice(["LEFT", "RIGHT"])
        arrow = word  # congruent
        trials.append((word, arrow))
    for _ in range(n_incongruent):
        word = random.choice(["LEFT", "RIGHT"])
        arrow = "LEFT" if word == "RIGHT" else "RIGHT"
        trials.append((word, arrow))
    random.shuffle(trials)
    return trials

# Feedback draw
def draw_feedback(surf, text, correct):
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    overlay.fill((0,0,0,80))
    surf.blit(overlay, (0,0))
    big = TITLE_FONT.render(text, True, CORRECT_GREEN if correct else WRONG_RED)
    surf.blit(big, big.get_rect(center=(SCREEN_SIZE[0]//2, SCREEN_SIZE[1]//2)))

# On-screen controls
left_button = Button((130, SCREEN_SIZE[1] - 120, 180, 80), "LEFT")
right_button = Button((SCREEN_SIZE[0] - 310, SCREEN_SIZE[1] - 120, 180, 80), "RIGHT")

# Main game loop variables
trials = make_trials(TRIALS, CONGRUENCY_PROPORTION)
trial_index = 0
score = 0
results = []  # list of dicts with trial info
state = "start"  # states: start, fixation, stimulus, feedback, finished
state_time = 0
stim_onset = None

# Start screen
def draw_start(surf):
    draw_gradient(surf, BG_TOP, BG_BOTTOM)
    title = TITLE_FONT.render("Directional / Spatial Stroop", True, CARD_COLOR)
    subtitle = SMALL_FONT.render("Respond to the WORD (not the arrow). Click or press ← / →", True, CARD_COLOR)
    surf.blit(title, title.get_rect(center=(SCREEN_SIZE[0]//2, 120)))
    surf.blit(subtitle, subtitle.get_rect(center=(SCREEN_SIZE[0]//2, 170)))
    # info card
    card = pygame.Rect(120, 220, SCREEN_SIZE[0]-240, 260)
    pygame.draw.rect(surf, CARD_COLOR, card, border_radius=16)
    info_lines = [
        f"Trials: {TRIALS}    Stimulus: {STIMULUS_DURATION}s    Fixation: {FIXATION_DURATION}s",
        "Scoring: +1 for correct (word). Reaction time recorded.",
        "Controls: Click LEFT / RIGHT buttons or press Left and Right arrow keys.",
        "Arrow distractor is shown to challenge spatial attention.",
        "Press SPACE to start."
    ]
    for i, line in enumerate(info_lines):
        txt = SMALL_FONT.render(line, True, TEXT_COLOR)
        surf.blit(txt, (card.x + 28, card.y + 28 + i*42))

# Draw progress and score
def draw_hud(surf, idx, total, score):
    # progress bar
    bar_w = SCREEN_SIZE[0] - 260
    bar_h = 14
    x = 130
    y = 40
    pygame.draw.rect(surf, (255,255,255,30), (x, y, bar_w, bar_h), border_radius=8)
    fill = int(bar_w * (idx/total))
    pygame.draw.rect(surf, ACCENT, (x, y, fill, bar_h), border_radius=8)
    # score
    scr = SMALL_FONT.render(f"Trial {idx}/{total}    Score: {score}", True, CARD_COLOR)
    surf.blit(scr, (x, y - 28))

# Main render for a stimulus trial
def draw_trial_screen(surf, word, arrow, time_left=None):
    draw_gradient(surf, BG_TOP, BG_BOTTOM)
    # HUD
    draw_hud(surf, trial_index+1, TRIALS, score)
    # central card for stimulus
    card = pygame.Rect(140, 120, SCREEN_SIZE[0]-280, 360)
    pygame.draw.rect(surf, CARD_COLOR, card, border_radius=18)
    # word text
    wtxt = WORD_FONT.render(word, True, TEXT_COLOR)
    surf.blit(wtxt, wtxt.get_rect(center=(SCREEN_SIZE[0]//2, SCREEN_SIZE[1]//2 - 20)))
    # arrow distractor on left/right side of word
    if SHOW_ARROW:
        arrow_x = SCREEN_SIZE[0]//2 - 220 if random_variant == 0 else SCREEN_SIZE[0]//2 + 220
        # We'll place arrow on a consistent side based on arrow_side for variety
        draw_arrow(surf, (arrow_x, SCREEN_SIZE[1]//2 - 10), 46, arrow, color=(60,60,80))
    # buttons
    mpos = pygame.mouse.get_pos()
    left_button.update(mpos)
    right_button.update(mpos)
    left_button.draw(surf)
    right_button.draw(surf)
    # timer small
    if time_left is not None:
        ttxt = SMALL_FONT.render(f"{time_left:.2f}s left", True, TEXT_COLOR)
        surf.blit(ttxt, (SCREEN_SIZE[0]//2 - 40, SCREEN_SIZE[1]-40))

# We'll add slight variation: arrow side alternate
random_variant = 0

# Fixation draw
def draw_fixation(surf):
    draw_gradient(surf, BG_TOP, BG_BOTTOM)
    draw_hud(surf, trial_index+1, TRIALS, score)
    # fixation cross
    cx, cy = SCREEN_SIZE[0]//2, SCREEN_SIZE[1]//2 - 20
    pygame.draw.line(surf, CARD_COLOR, (cx-14, cy), (cx+14, cy), 5)
    pygame.draw.line(surf, CARD_COLOR, (cx, cy-14), (cx, cy+14), 5)

# End screen
def draw_finished(surf):
    draw_gradient(surf, BG_TOP, BG_BOTTOM)
    title = TITLE_FONT.render("Session complete!", True, CARD_COLOR)
    surf.blit(title, title.get_rect(center=(SCREEN_SIZE[0]//2, 120)))
    score_text = SMALL_FONT.render(f"Score: {score} / {TRIALS}", True, CARD_COLOR)
    surf.blit(score_text, score_text.get_rect(center=(SCREEN_SIZE[0]//2, 180)))
    # Show simple summary table
    lines = [
        f"Trials: {TRIALS}",
        f"Average RT (correct): {calc_avg_rt():.3f} s" if any(r['correct'] for r in results) else "No correct responses.",
        "Press R to restart or Q to quit."
    ]
    for i, l in enumerate(lines):
        surf.blit(SMALL_FONT.render(l, True, CARD_COLOR), (SCREEN_SIZE[0]//2 - 200, 240 + i*40))

def calc_avg_rt():
    if not results:
        return 0.0
    correct_rts = [r['rt'] for r in results if r['correct']]
    if not correct_rts:
        return 0.0
    return sum(correct_rts)/len(correct_rts)

# Main loop
running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    t = time.time()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if state == "start":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                trial_index = 0
                score = 0
                results = []
                trials = make_trials(TRIALS, CONGRUENCY_PROPORTION)
                state = "fixation"
                state_time = t
                random_variant = random.randint(0, 1)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # start on click too
                trial_index = 0
                score = 0
                results = []
                trials = make_trials(TRIALS, CONGRUENCY_PROPORTION)
                state = "fixation"
                state_time = t
                random_variant = random.randint(0, 1)

        elif state == "fixation":
            # nothing clickable
            if t - state_time >= FIXATION_DURATION:
                # move to stimulus
                state = "stimulus"
                state_time = t
                stim_onset = t
                current_word, current_arrow = trials[trial_index]
                # Choose arrow side variant
                random_variant = random.randint(0,1)

        elif state == "stimulus":
            # handle responses
            response = None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    response = "LEFT"
                if event.key == pygame.K_RIGHT:
                    response = "RIGHT"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mpos = event.pos
                if left_button.clicked(mpos):
                    response = "LEFT"
                elif right_button.clicked(mpos):
                    response = "RIGHT"

            if response is not None:
                rt = t - stim_onset
                correct = (response == current_word)  # **CRITICAL**: correctness judged by WORD (not arrow)
                if correct:
                    score += 1
                results.append({
                    'trial': trial_index + 1,
                    'word': current_word,
                    'arrow': current_arrow,
                    'response': response,
                    'correct': correct,
                    'rt': rt,
                })
                # go to feedback
                state = "feedback"
                state_time = t
                feedback_text = "Correct!" if correct else "Wrong!"
                feedback_color = CORRECT_GREEN if correct else WRONG_RED

            # time out (no response)
            if t - stim_onset >= STIMULUS_DURATION and state == "stimulus":
                # record miss as wrong with rt = None
                results.append({
                    'trial': trial_index + 1,
                    'word': current_word,
                    'arrow': current_arrow,
                    'response': None,
                    'correct': False,
                    'rt': None,
                })
                state = "feedback"
                state_time = t
                feedback_text = "Too Slow!"
                feedback_color = WRONG_RED

        elif state == "feedback":
            # wait for FEEDBACK_DURATION then next trial / finish
            if t - state_time >= FEEDBACK_DURATION:
                trial_index += 1
                if trial_index >= TRIALS:
                    state = "finished"
                else:
                    state = "fixation"
                state_time = t

        elif state == "finished":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    state = "start"
                if event.key == pygame.K_q:
                    running = False

    # Drawing section per state
    if state == "start":
        draw_start(screen)

    elif state == "fixation":
        draw_fixation(screen)

    elif state == "stimulus":
        # compute time left for display
        elapsed = t - stim_onset
        time_left = max(0.0, STIMULUS_DURATION - elapsed)
        # get current stimulus
        current_word, current_arrow = trials[trial_index]
        # draw trial screen with arrow on left or right side (random_variant)
        # modify draw_trial_screen to use current random_variant arrow side
        # We'll temporarily set random_variant side and call draw_trial_screen
        draw_gradient(screen, BG_TOP, BG_BOTTOM)
        draw_hud(screen, trial_index+1, TRIALS, score)
        # card
        card = pygame.Rect(140, 120, SCREEN_SIZE[0]-280, 360)
        pygame.draw.rect(screen, CARD_COLOR, card, border_radius=18)
        # word text
        wtxt = WORD_FONT.render(current_word, True, TEXT_COLOR)
        screen.blit(wtxt, wtxt.get_rect(center=(SCREEN_SIZE[0]//2, SCREEN_SIZE[1]//2 - 20)))
        # arrow distractor
        if SHOW_ARROW:
            arrow_x = SCREEN_SIZE[0]//2 - 220 if random_variant == 0 else SCREEN_SIZE[0]//2 + 220
            draw_arrow(screen, (arrow_x, SCREEN_SIZE[1]//2 - 10), 46, current_arrow, color=(60,60,80))
        # buttons
        mpos = pygame.mouse.get_pos()
        left_button.update(mpos)
        right_button.update(mpos)
        left_button.draw(screen)
        right_button.draw(screen)
        # timer
        ttxt = SMALL_FONT.render(f"{time_left:.2f}s left", True, TEXT_COLOR)
        screen.blit(ttxt, (SCREEN_SIZE[0]//2 - 40, SCREEN_SIZE[1]-40))

    elif state == "feedback":
        # draw the last stimulus faintly
        draw_gradient(screen, BG_TOP, BG_BOTTOM)
        draw_hud(screen, trial_index+1, TRIALS, score)
        card = pygame.Rect(140, 120, SCREEN_SIZE[0]-280, 360)
        pygame.draw.rect(screen, CARD_COLOR, card, border_radius=18)
        # show the stimulus faint
        current = results[-1]
        wtxt = WORD_FONT.render(current['word'], True, (100,100,110))
        screen.blit(wtxt, wtxt.get_rect(center=(SCREEN_SIZE[0]//2, SCREEN_SIZE[1]//2 - 20)))
        if SHOW_ARROW:
            arrow_x = SCREEN_SIZE[0]//2 - 220 if random_variant == 0 else SCREEN_SIZE[0]//2 + 220
            draw_arrow(screen, (arrow_x, SCREEN_SIZE[1]//2 - 10), 46, current['arrow'], color=(140,140,150))
        # feedback overlay
        last_correct = current['correct']
        fb_text = "Correct!" if last_correct else ("Too Slow!" if current['response'] is None else "Wrong!")
        draw_feedback(screen, fb_text, last_correct)

    elif state == "finished":
        # show end summary
        draw_gradient(screen, BG_TOP, BG_BOTTOM)
        title = TITLE_FONT.render("Session complete!", True, CARD_COLOR)
        screen.blit(title, title.get_rect(center=(SCREEN_SIZE[0]//2, 120)))
        score_text = SMALL_FONT.render(f"Score: {score} / {TRIALS}", True, CARD_COLOR)
        screen.blit(score_text, score_text.get_rect(center=(SCREEN_SIZE[0]//2, 180)))
        avg = calc_avg_rt()
        lines = [
            f"Trials: {TRIALS}",
            f"Average RT (correct): {avg:.3f} s" if avg>0 else "Average RT (correct): N/A",
            "Press R to restart or Q to quit."
        ]
        for i, l in enumerate(lines):
            screen.blit(SMALL_FONT.render(l, True, CARD_COLOR), (SCREEN_SIZE[0]//2 - 200, 240 + i*40))

    pygame.display.flip()

pygame.quit()
sys.exit()
