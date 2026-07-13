import { Alert, Badge, Button, Group, Stack, Text, Title } from "@mantine/core";
import { useMemo, useState } from "react";
import type { Flashcard } from "../types";

export function FlashcardResult({ cards }: { cards: Flashcard[] }) {
  const original = useMemo(() => [...cards].sort((a, b) => a.sort_order - b.sort_order), [cards]);
  const [deck, setDeck] = useState(original);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [ratings, setRatings] = useState<Record<string, boolean>>({});
  if (!deck.length) return <Alert color="gray">暂无可复习卡片</Alert>;
  const card = deck[index];
  const roundComplete = deck.every((item) => Object.hasOwn(ratings, item.id));
  const rate = (known: boolean) => { setRatings((r) => ({ ...r, [card.id]: known })); if (index < deck.length - 1) { setIndex(index + 1); setFlipped(false); } };
  return <Stack align="stretch" gap="md">
    <Group justify="space-between"><Text size="sm">{index + 1} / {deck.length}</Text><Button onClick={() => { setDeck([...deck].sort(() => Math.random() - 0.5)); setIndex(0); setFlipped(false); }} variant="subtle">打乱</Button></Group>
    <button aria-label="翻转卡片" className="gc-flashcard" onClick={() => setFlipped(!flipped)} type="button"><Badge variant="light">{flipped ? "背面" : "正面"}</Badge><Title order={3}>{flipped ? card.back : card.front}</Title>{flipped && card.explanation ? <Text>{card.explanation}</Text> : null}</button>
    {flipped ? <Group grow><Button color="red" onClick={() => rate(false)} variant="light">未掌握</Button><Button color="teal" onClick={() => rate(true)} variant="light">已掌握</Button></Group> : null}
    <Group justify="space-between"><Button disabled={index === 0} onClick={() => { setIndex(index - 1); setFlipped(false); }} variant="default">上一张</Button><Button disabled={index === deck.length - 1} onClick={() => { setIndex(index + 1); setFlipped(false); }}>下一张</Button></Group>
    {roundComplete ? <Group justify="center"><Button onClick={() => { setDeck(original); setIndex(0); setRatings({}); setFlipped(false); }} variant="default">练习全部</Button><Button disabled={!deck.some((item) => ratings[item.id] === false)} onClick={() => { setDeck(deck.filter((item) => ratings[item.id] === false)); setIndex(0); setRatings({}); setFlipped(false); }}>只练未掌握</Button></Group> : null}
  </Stack>;
}
