// 发布/编辑帖子时，根据标题自动推断「物品」和「地点」并填入，
// 只在用户尚未手动填写时填充，用户随时可以自行修改。
(function () {
  "use strict";

  // 地点关键词（按长度从长到短排列，确保优先匹配更具体的词）
  var LOC_TOKENS = [
    "图书馆", "体育馆", "教学楼", "实验楼", "综合楼", "行政楼", "宿舍楼",
    "实验室", "运动场", "停车场", "篮球场", "足球场", "自习室", "阅览室",
    "号楼", "教室", "食堂", "餐厅", "操场", "球场", "宿舍", "公寓", "广场",
    "机房", "大厅", "校区", "楼", "馆"
  ];

  var LOC_RE = new RegExp(
    "[\\u4e00-\\u9fa5A-Za-z0-9]{0,6}(?:" + LOC_TOKENS.join("|") + ")" +
    "([A-Za-z]?\\d{1,4}号?室?)?"
  );

  function parseTitle(title) {
    var result = { item: "", location: "" };
    title = (title || "").trim();
    if (!title) {
      return result;
    }

    var parts = title.split(/[\s,，、;；/]+/).filter(Boolean);
    var rest = [];

    for (var i = 0; i < parts.length; i++) {
      if (!result.location) {
        var m = parts[i].match(LOC_RE);
        if (m && m[0] && m[0].length >= 2 && !/^\d+$/.test(m[0])) {
          result.location = m[0];
          var leftover = parts[i].replace(m[0], "").trim();
          if (leftover) {
            rest.push(leftover);
          }
          continue;
        }
      }
      rest.push(parts[i]);
    }

    result.item = rest.join(" ").trim();
    return result;
  }

  function init() {
    var form = document.querySelector("form");
    if (!form) {
      return;
    }
    var titleEl = form.querySelector('input[name="title"]');
    var itemEl = form.querySelector('input[name="item_name"]');
    var locEl = form.querySelector('input[name="location"]');
    if (!titleEl || !itemEl || !locEl) {
      return;
    }

    // 若字段已有内容（如编辑已有帖子），视为用户已填写，不覆盖。
    var itemEdited = itemEl.value.trim() !== "";
    var locEdited = locEl.value.trim() !== "";
    itemEl.addEventListener("input", function () { itemEdited = true; });
    locEl.addEventListener("input", function () { locEdited = true; });

    function apply() {
      var parsed = parseTitle(titleEl.value);
      if (!itemEdited && parsed.item) {
        itemEl.value = parsed.item;
      }
      if (!locEdited && parsed.location) {
        locEl.value = parsed.location;
      }
    }

    titleEl.addEventListener("input", apply);
    titleEl.addEventListener("blur", apply);
    if (titleEl.value.trim()) {
      apply();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
