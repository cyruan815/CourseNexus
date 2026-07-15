import { Alert, Button, Group, Menu, Modal, Stack, TextInput, Textarea } from "@mantine/core";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Flashcard } from "../types";
import { updateFlashcards } from "../../course-workspace/api";
import { flashcards } from "../guards";

type Feedback = "correct" | "incorrect" | null;

export function FlashcardResult({ cards, generatedContentId = "test-generated-content" }: { cards: Flashcard[]; generatedContentId?: string }) {
  const initialCards = useMemo(() => [...cards].sort((a, b) => a.sort_order - b.sort_order), [cards]);
  const [savedCards, setSavedCards] = useState(initialCards);
  const [deck, setDeck] = useState(initialCards);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [ratings, setRatings] = useState<Record<string, boolean>>({});
  const [addOpen, setAddOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [explanation, setExplanation] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
  }, []);

  if (!deck.length) return <Alert color="gray">暂无可复习卡片</Alert>;

  const card = deck[index];
  const correctCount = Object.values(ratings).filter(Boolean).length;
  const incorrectCount = Object.values(ratings).filter((value) => value === false).length;
  const roundComplete = deck.every((item) => Object.hasOwn(ratings, item.id));

  const moveTo = (nextIndex: number) => {
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
    setIndex(nextIndex);
    setFlipped(false);
    setFeedback(null);
  };

  const rate = (known: boolean) => {
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
    setRatings((current) => ({ ...current, [card.id]: known }));
    setFlipped(false);
    setFeedback(known ? "correct" : "incorrect");
    advanceTimer.current = setTimeout(() => {
      if (index < deck.length - 1) setIndex(index + 1);
      setFlipped(false);
      setFeedback(null);
      advanceTimer.current = null;
    }, 1000);
  };

  const reset = (nextDeck: Flashcard[]) => {
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
    setDeck(nextDeck);
    setIndex(0);
    setRatings({});
    setFlipped(false);
    setFeedback(null);
  };

  const persist = async (nextDeck: Flashcard[]) => {
    setSaving(true); setSaveError(null);
    try {
      const updated = await updateFlashcards(generatedContentId, nextDeck.map(({ front, back, tags, explanation }) => ({ front, back, tags, explanation })));
      const saved = flashcards(updated.content_json);
      if (!saved) throw new Error("保存后的卡片数据不可读取");
      setSavedCards(saved); setDeck(saved); setIndex((current) => Math.min(current, saved.length - 1)); setFeedback(null); setFlipped(false); setRatings({});
      return true;
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "卡片保存失败");
      return false;
    } finally { setSaving(false); }
  };

  const addCard = async () => {
    if (!front.trim() || !back.trim()) return;
    const ok = await persist([...savedCards, { id: "card_new", sort_order: savedCards.length + 1, front: front.trim(), back: back.trim(), tags: [], mastery_status: "unknown", explanation: explanation.trim() || null }]);
    if (ok) { setAddOpen(false); setFront(""); setBack(""); setExplanation(""); }
  };

  const deleteCard = async () => {
    if (savedCards.length <= 1) return;
    const ok = await persist(savedCards.filter((savedCard) => savedCard.id !== card.id));
    if (ok) setDeleteOpen(false);
  };

  return (
    <section className="gc-flashcard-shell">
      <Group className="gc-flashcard-toolbar" justify="space-between">
        <div className="gc-flashcard-brand">
          <span aria-hidden="true" className="gc-flashcard-logo">✦</span>
          <h2>知识闪卡</h2>
        </div>
        <Group gap="xs">
          <Button aria-label="打乱卡片" className="gc-flashcard-shuffle" onClick={() => reset([...deck].sort(() => Math.random() - 0.5))} variant="default">打乱</Button>
          <Menu position="bottom-end" shadow="md" width={180}>
            <Menu.Target><button aria-label="更多操作" className="gc-flashcard-more" type="button">⋯</button></Menu.Target>
            <Menu.Dropdown><Menu.Item onClick={() => setAddOpen(true)}>添加卡片</Menu.Item><Menu.Item color="red" disabled={savedCards.length <= 1} onClick={() => setDeleteOpen(true)}>删除当前卡片</Menu.Item></Menu.Dropdown>
          </Menu>
        </Group>
      </Group>

      <div className="gc-flashcard-progress-row">
        <span>{index + 1} / {deck.length}</span>
        <div aria-hidden="true" className="gc-flashcard-progress"><span style={{ width: `${((index + 1) / deck.length) * 100}%` }} /></div>
        <span>{Object.keys(ratings).length ? `已完成 ${Object.keys(ratings).length} 张` : "待复习"}</span>
      </div>

      <div className="gc-flashcard-stage">
        {feedback ? (
          <div className={`gc-flashcard gc-flashcard-feedback gc-flashcard-${feedback}`}>
            <h3>{feedback === "correct" ? "答对了！" : "再接再厉"}</h3>
            <p>{feedback === "correct" ? "记得很牢，继续保持。" : "没关系，再看一遍就会更熟悉。"}</p>
          </div>
        ) : flipped ? (
          <button aria-label="翻转回问题" className="gc-flashcard gc-flashcard-answer" onClick={() => setFlipped(false)} type="button">
            <div className="gc-flashcard-meta"><span className="gc-flashcard-side">答案</span><span aria-hidden="true">⋯</span></div>
            <h3>{card.back}</h3>
            {card.explanation ? <p className="gc-flashcard-explanation">{card.explanation}</p> : null}
          </button>
        ) : (
          <button aria-label="翻转查看答案" className="gc-flashcard gc-flashcard-question" onClick={() => setFlipped(true)} type="button">
            <div className="gc-flashcard-meta"><span className="gc-flashcard-side">问题</span><span aria-hidden="true">⋯</span></div>
            <h3>{card.front}</h3>
          </button>
        )}
      </div>

      <div className="gc-flashcard-controls">
        <button aria-label="上一张" className="gc-flashcard-nav" disabled={index === 0} onClick={() => moveTo(index - 1)} type="button">←</button>
        <button aria-label={`答错 ${incorrectCount}`} className="gc-flashcard-score gc-flashcard-score-wrong" onClick={() => rate(false)} type="button"><span>×</span>{incorrectCount}</button>
        <button aria-label={`答对 ${correctCount}`} className="gc-flashcard-score gc-flashcard-score-right" onClick={() => rate(true)} type="button">{correctCount}<span>✓</span></button>
        <button aria-label="下一张" className="gc-flashcard-nav" disabled={index === deck.length - 1} onClick={() => moveTo(index + 1)} type="button">→</button>
      </div>

      {roundComplete ? (
        <Stack align="center" className="gc-flashcard-retry" gap="sm">
          <Group justify="center">
            <Button onClick={() => reset(savedCards)} variant="default">练习全部</Button>
            <Button disabled={!deck.some((item) => ratings[item.id] === false)} onClick={() => reset(deck.filter((item) => ratings[item.id] === false))}>只练未掌握</Button>
          </Group>
        </Stack>
      ) : null}
      {saveError ? <Alert color="red" mt="md" role="alert">{saveError}</Alert> : null}
      <Modal onClose={() => setAddOpen(false)} opened={addOpen} title="添加卡片">
        <Stack><Textarea label="问题" onChange={(event) => setFront(event.currentTarget.value)} required value={front} /><Textarea label="答案" onChange={(event) => setBack(event.currentTarget.value)} required value={back} /><TextInput label="补充解释（可选）" onChange={(event) => setExplanation(event.currentTarget.value)} value={explanation} /><Group justify="flex-end"><Button onClick={() => setAddOpen(false)} variant="default">取消</Button><Button disabled={!front.trim() || !back.trim()} loading={saving} onClick={addCard}>保存卡片</Button></Group></Stack>
      </Modal>
      <Modal onClose={() => setDeleteOpen(false)} opened={deleteOpen} title="删除当前卡片">
        <Stack><p>确定删除“{card.front}”吗？删除后将永久保存。</p><Group justify="flex-end"><Button onClick={() => setDeleteOpen(false)} variant="default">取消</Button><Button color="red" loading={saving} onClick={deleteCard}>确认删除</Button></Group></Stack>
      </Modal>
    </section>
  );
}
