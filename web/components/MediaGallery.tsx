'use client'

import { useState } from 'react'

import type { Media } from '../lib/report'
import { HeroMedia } from './HeroMedia'
import { Lightbox } from './Lightbox'
import { MediaStrip } from './MediaStrip'

/** 대표와 미디어 줄. 누른 미디어부터 크게 본다. */
export function MediaGallery({ media }: { media: Media[] }) {
  const [opened, setOpened] = useState<number | null>(null)
  return (
    <>
      <HeroMedia media={media[0]} index={0} total={media.length} onOpen={() => setOpened(0)} />
      {media.length > 1 && <MediaStrip media={media} onOpen={setOpened} />}
      {opened !== null && <Lightbox media={media} start={opened} onClose={() => setOpened(null)} />}
    </>
  )
}
