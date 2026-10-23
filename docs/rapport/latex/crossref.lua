-- Numérotation par chapitre des figures, tableaux et codes, et renvois [@fig:x], [@tab:x], [@code:x].
-- LaTeX numérote lui-même : on ne fait que poser les \label et écrire des \ref.
-- Word ne numérote rien : on écrit « Figure 3.1 », « Tableau 3.1 », « Code 3.1 » dans les légendes
-- et les numéros dans le texte, et on ajoute les numéros de ligne aux codes (le texte y renvoie).

local is_latex = FORMAT:match("latex") ~= nil
local chapter, counters, numbers, pending_table = 0, {}, {}, nil

local function next_number(kind)
  counters[kind] = (counters[kind] or 0) + 1
  return chapter .. "." .. counters[kind]
end

local function prefix(label, number)
  return { pandoc.Strong({ pandoc.Str(label .. " " .. number) }), pandoc.Str(" – ") }
end

local function prepend_to_caption(blocks, inlines)
  if #blocks == 0 then
    blocks:insert(pandoc.Plain(inlines))
  else
    blocks[1].content = inlines .. blocks[1].content
  end
end

local number_pass = {
  traverse = "topdown",

  Header = function(h)
    if h.level ~= 1 then return nil end
    if not h.classes:includes("unnumbered") then
      chapter, counters = chapter + 1, {}
    elseif is_latex then
      -- \chapter* ne met pas à jour l'en-tête de page
      return { h, pandoc.RawBlock("latex", "\\markboth{" .. pandoc.utils.stringify(h) .. "}{}") }
    end
  end,

  Figure = function(fig)
    local n = next_number("fig")
    if fig.identifier ~= "" then numbers[fig.identifier] = n end
    if not is_latex then
      prepend_to_caption(fig.caption.long, pandoc.List(prefix("Figure", n)))
      return fig
    end
  end,

  Div = function(div)
    if div.identifier:match("^tab:") then pending_table = div.identifier end
  end,

  Table = function(tbl)
    local n = next_number("tab")
    local id = pending_table
    pending_table = nil
    if id then numbers[id] = n end
    if is_latex then
      if id then
        prepend_to_caption(tbl.caption.long, pandoc.List({ pandoc.RawInline("latex", "\\label{" .. id .. "}") }))
      end
    else
      prepend_to_caption(tbl.caption.long, pandoc.List(prefix("Tableau", n)))
    end
    return tbl
  end,

  CodeBlock = function(code)
    local caption = code.attributes.caption
    if not caption then return nil end
    local n = next_number("code")
    if code.identifier ~= "" then numbers[code.identifier] = n end
    if is_latex then return nil end
    local lines, numbered = {}, {}
    for line in (code.text .. "\n"):gmatch("(.-)\n") do lines[#lines + 1] = line end
    local width = #tostring(#lines)
    for i, line in ipairs(lines) do
      numbered[i] = string.format("%" .. width .. "d  %s", i, line)
    end
    code.text = table.concat(numbered, "\n")
    code.attributes.caption = nil
    local title = pandoc.Para(pandoc.List(prefix("Code", n)) .. pandoc.List({ pandoc.Str(caption) }))
    return { title, code }
  end,
}

local reference_pass = {
  Cite = function(cite)
    local id = cite.citations[1].id
    if not numbers[id] then return nil end
    if is_latex then return pandoc.RawInline("latex", "\\ref{" .. id .. "}") end
    return pandoc.Str(numbers[id])
  end,
}

return { number_pass, reference_pass }
