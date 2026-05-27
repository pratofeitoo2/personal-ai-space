---
title: Dataview vs Datacore vs Obsidian Bases
author:
  - "[[Tim Miller]]"
created: 2025-12-05
description: "Lately there’s been a lot of buzz about Datacore and Obsidian Bases. And for good reason! For most of Obsidian’s existence we’ve only had a single good option for querying notes in Obsidian: Dataview. As you may know, I am a huge Dataview fan. Dataview paved the way and clearly showcased why we need options […]"
tags:
  - clippings
updated: 2025-12-05T21:44
---
Lately there’s been a lot of buzz about Datacore and Obsidian Bases.

And for good reason! For most of Obsidian’s existence we’ve only had a single good option for querying notes in Obsidian: [Dataview](https://obsidian.rocks/dataview-in-obsidian-a-beginners-guide/).

As you may know, I am a huge Dataview fan. Dataview paved the way and clearly showcased why we need options for querying notes in Obsidian.

But it’s no longer the only kid on the block!

Many people have been asking me about the differences between Dataview and these new tools, so I thought I would address the differences once and for all.

> Note: this will likely change in the next month or two, but at the moment, Datacore and Bases are both in *beta*. They are fully operational, but under heavy development and likely to change before they go public.
> 
> This is a high level overview, we won’t go into specifics about these beta plugins.

## Dataview

![](https://i0.wp.com/obsidian.rocks/wp-content/uploads/2025/06/image.png?w=1008&ssl=1)

Dataview is the original. It was first released in 2021, and it took the Obsidian community by storm.

It is one of the most downloaded plugins for Obsidian of all time, as of today garnering nearly **3 million** downloads.

It allows you to query your notes quickly and effectively, using a simple query language. For instance, you can list all notes with a certain tag like this:  
`<pre> LIST from #tag </pre>`  
For more about how Dataview works, see [Getting Started with Dataview](https://obsidian.rocks/dataview-in-obsidian-a-beginners-guide/).

Dataview is great. But, unfortunately, it has some issues.

The first is performance. Dataview performs well for what it is, but it gets sluggish if you’re using it with large vaults. The query language is nice, but it wasn’t designed for speed.

The plugin also takes time to load, especially on mobile. I found on my phone that it consistently added around a second or two to the app load time, and sometimes much more than that.

In addition to speed problems, it hasn’t received any significant updates in a long time. The main developer has been focused on other things, so growth has stopped.

No updates isn’t *necessarily* a bad thing, but it does mean that our other options have a distinct advantage, because they are improving over time, whereas Dataview is stagnant.

Dataview also isn’t *interactive*. It’s great for gathering and viewing data, but there’s almost nothing you can *do* other than *view* the data.

On the *plus* side Dataview is very *stable*. It has been used by hundreds of thousands of people, and received updates and bug fixes for several years. You can write your queries with the knowledge that they won’t easily break, which is a nice perk.

Also, at the moment, it’s the only plugin on this list that isn’t in beta. If you’re looking for a query language for your notes *right now* then Dataview is the clear choice (see [Getting Started with Dataview](https://obsidian.rocks/dataview-in-obsidian-a-beginners-guide/) for more).

But if you *aren’t* in a hurry, you might be more interested in one of the other two options.

## Datacore

![](https://i0.wp.com/obsidian.rocks/wp-content/uploads/2025/06/image-1.png?w=1015&ssl=1)

Datacore is the successor to Dataview. It’s designed to fix the speed problems of Dataview, and also to add more interactivity.

Datacore is way faster than Dataview. It feels more “native”. When using DV, you often see “unstyled notes”, where the content is shuffling around as DV renders things. Datacore fixes this: most of the time when you open a note with DC, the content is *just there*. It feels faster and smoother in every situation.

There are no perfect solutions though, and with this benefits come some tradeoffs.

The big downside to DC is *accessibility*. DV had a nice friendly query syntax that was easy to learn and use. Datacore scraps that, and forces you to build components using React.

React gives you a *ton* of power and control, but looks a lot more arcane and cryptic to the average user.

So Datacore is better once you have working scripts, but writing your own scripts is trickier.

I think Datacore is going to be great for *reusable components*. I envision libraries of “Datacore components” that you can pull into your vault, tweak the configuration a bit, and be off to the races. I think that’s where DC will really shine.

Not only does Datacore allow you to create custom views, in much the same way as Dataview, but it also allows you to interact with your notes more. You can create new notes, edit properties, and much more using Datacore.

The developer of Datacore has also mentioned that he wants to create a visual editor for Datacore, which could be a solution to how complex the language is. If Michael successfully creates a visual editor that makes the language accessible, then Datacore could truly become as popular as its little brother.

To learn more about Datacore, see [Getting Started with Datacore](https://obsidian.rocks/getting-started-with-datacore/).

## Bases

![](https://i0.wp.com/obsidian.rocks/wp-content/uploads/2025/06/image-2.png?resize=1024%2C444&ssl=1)

Bases are a new initiative from the Obsidian Team themselves. One could view this as “the official Dataview”. They are currently in Beta, and only available in [early access](https://help.obsidian.md/early-access), but they will be available to everyone soon, probably in the next month or two.

I’m guessing that the Obsidian team has been planning Bases for a long time, because even though they are currently in beta, they are very well done. You can tell they’ve taken inspiration from several different community plugins, and created something unique.

Bases are incredibly powerful. They are fast to create, fast to update, and return results *incredibly* fast. I don’t know how the Obsidian team did it, but if you want raw *speed* in your queries, Bases are for you.

In my experience, they’re even faster than Datacore, and without the downside of having to learn a programming language.

That’s right! Unlike both DV and DC, Bases don’t require *any* coding. You can create and edit Bases entirely with a visual editor.

Bases do have their limits though: at the moment, they only support *table views* and they can only query data that is stored in *properties*. Those are fairly big limitations, but it is amazing what you can do with Bases nonetheless.

## In Conclusion

Dataview, Datacore, and Bases all bring important things to the table.

Dataview has been my friend and companion for a long time. I love how easy it is to create a Dataview script. But, once DC and Bases are freely available, I will probably transition away. Dataview is just too slow, and with the lack of updates that will probably get worse over time.

For simple things, I will use Bases. I like that they’re built-in to the app, they’re wicked fast, and the visual editor makes them quick to create and update. Over the last week alone I’ve created over a dozen Bases, and I use them every day.

For more complex, interactive components, I will turn to Datacore. With Datacore truly *anything* is possible, so I think it will still have a place in my vault.