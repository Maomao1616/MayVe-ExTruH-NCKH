// Đối chiếu lib/paper.js với backend (layout.py). Sinh bởi script từ chính backend — chạy: node --test frontend/tests/paper.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { plan, mapPoint, matrix, fitBox, innerArea, rotatedSize } from "../js/lib/paper.js";

const PAPERS = { a4: [210, 297], a5: [148, 210], a6: [105, 148], letter: [215.9, 279.4] };
const MACHINE = { workW: 285, workH: 318 };
const SRC = { x: 10, y: 20, w: 40, h: 10 };
const POINTS = [[10.0, 20.0], [50.0, 30.0], [30.0, 25.0], [10.0, 30.0]];
const CASES = [
 {
  "name": "a4 mặc định",
  "raw": {
   "paper": "a4"
  },
  "expect": {
   "ok": true,
   "box": [
    5.0,
    5.0,
    200.0,
    287.0
   ],
   "paper": [
    0.0,
    0.0,
    210.0,
    297.0
   ],
   "points": [
    [
     5.0,
     123.5
    ],
    [
     205.0,
     173.5
    ],
    [
     105.0,
     148.5
    ],
    [
     5.0,
     173.5
    ]
   ]
  }
 },
 {
  "name": "a5 xoay 90",
  "raw": {
   "paper": "a5",
   "rotate": 90
  },
  "expect": {
   "ok": true,
   "box": [
    5.0,
    5.0,
    138.0,
    200.0
   ],
   "paper": [
    0.0,
    0.0,
    148.0,
    210.0
   ],
   "points": [
    [
     99.0,
     5.0
    ],
    [
     49.0,
     205.0
    ],
    [
     74.0,
     105.0
    ],
    [
     49.0,
     5.0
    ]
   ]
  }
 },
 {
  "name": "a6 xoay 180 lật X",
  "raw": {
   "paper": "a6",
   "rotate": 180,
   "flip_x": true
  },
  "expect": {
   "ok": true,
   "box": [
    5.0,
    5.0,
    95.0,
    138.0
   ],
   "paper": [
    0.0,
    0.0,
    105.0,
    148.0
   ],
   "points": [
    [
     5.0,
     85.875
    ],
    [
     100.0,
     62.125
    ],
    [
     52.5,
     74.0
    ],
    [
     5.0,
     62.125
    ]
   ]
  }
 },
 {
  "name": "a4 xoay 270 lật Y lề 10",
  "raw": {
   "paper": "a4",
   "rotate": 270,
   "flip_y": true,
   "margin_mm": 10
  },
  "expect": {
   "ok": true,
   "box": [
    10.0,
    10.0,
    190.0,
    277.0
   ],
   "paper": [
    0.0,
    0.0,
    210.0,
    297.0
   ],
   "points": [
    [
     70.375,
     10.0
    ],
    [
     139.625,
     287.0
    ],
    [
     105.0,
     148.5
    ],
    [
     139.625,
     10.0
    ]
   ]
  }
 },
 {
  "name": "khung nhỏ lệch tay",
  "raw": {
   "paper": "a4",
   "width_mm": 80,
   "height_mm": 40,
   "center": false,
   "offset_x_mm": 12,
   "offset_y_mm": 30
  },
  "expect": {
   "ok": true,
   "box": [
    17.0,
    35.0,
    80.0,
    40.0
   ],
   "paper": [
    0.0,
    0.0,
    210.0,
    297.0
   ],
   "points": [
    [
     17.0,
     45.0
    ],
    [
     97.0,
     65.0
    ],
    [
     57.0,
     55.0
    ],
    [
     17.0,
     65.0
    ]
   ]
  }
 },
 {
  "name": "kéo giãn",
  "raw": {
   "paper": "a4",
   "fit": "stretch",
   "width_mm": 100,
   "height_mm": 100
  },
  "expect": {
   "ok": true,
   "box": [
    55.0,
    98.5,
    100.0,
    100.0
   ],
   "paper": [
    0.0,
    0.0,
    210.0,
    297.0
   ],
   "points": [
    [
     55.0,
     98.5
    ],
    [
     155.0,
     198.5
    ],
    [
     105.0,
     148.5
    ],
    [
     55.0,
     198.5
    ]
   ]
  }
 },
 {
  "name": "giấy tùy chọn",
  "raw": {
   "paper": "custom",
   "paper_width_mm": 120,
   "paper_height_mm": 90,
   "margin_mm": 3
  },
  "expect": {
   "ok": true,
   "box": [
    3.0,
    3.0,
    114.0,
    84.0
   ],
   "paper": [
    0.0,
    0.0,
    120.0,
    90.0
   ],
   "points": [
    [
     3.0,
     30.75
    ],
    [
     117.0,
     59.25
    ],
    [
     60.0,
     45.0
    ],
    [
     3.0,
     59.25
    ]
   ]
  }
 },
 {
  "name": "khung vượt giấy",
  "raw": {
   "paper": "a6",
   "width_mm": 200,
   "height_mm": 200
  },
  "expect": {
   "ok": false,
   "code": "box_out_of_paper"
  }
 },
 {
  "name": "giấy vượt vùng máy",
  "raw": {
   "paper": "custom",
   "paper_width_mm": 300,
   "paper_height_mm": 90
  },
  "expect": {
   "ok": false,
   "code": "paper_out_of_area"
  }
 }
];

// Dựng layout JS từ các khóa của backend (cùng giá trị mặc định với spec.py).
function layoutOf(raw) {
    const paper = raw.paper ?? "a4";
    const [pw, ph] = paper === "custom" ? [raw.paper_width_mm, raw.paper_height_mm] : PAPERS[paper];
    return {
        paperW: pw, paperH: ph, paperX: 0, paperY: 0, margin: raw.margin_mm ?? 5,
        width: raw.width_mm ?? null, height: raw.height_mm ?? null, fit: raw.fit ?? "contain",
        center: raw.center ?? true, offsetX: raw.offset_x_mm ?? 0, offsetY: raw.offset_y_mm ?? 0,
        flipX: raw.flip_x ?? false, flipY: raw.flip_y ?? false, rotate: raw.rotate ?? 0
    };
}
const near = (a, b, msg) => assert.ok(Math.abs(a - b) < 1e-6, `${msg}: ${a} != ${b}`);

for (const c of CASES) {
    test(`bố trí khớp backend: ${c.name}`, () => {
        const pl = plan(SRC, layoutOf(c.raw), MACHINE);
        if (!c.expect.ok) {
            assert.equal(pl.ok, false);
            assert.equal(pl.code, c.expect.code);
            return;
        }
        assert.equal(pl.ok, true);
        const { box, paper } = c.expect;
        [pl.box.x, pl.box.y, pl.box.w, pl.box.h].forEach((v, i) => near(v, box[i], `box[${i}]`));
        [pl.paper.x, pl.paper.y, pl.paper.w, pl.paper.h].forEach((v, i) => near(v, paper[i], `paper[${i}]`));
        const m = matrix(pl);
        POINTS.forEach(([x, y], i) => {
            const [ex, ey] = c.expect.points[i];
            const [mx, my] = mapPoint(pl, x, y);
            near(mx, ex, `x${i}`); near(my, ey, `y${i}`);
            // ma trận canvas cho cùng kết quả
            near(m[0] * x + m[2] * y + m[4], ex, `mx${i}`); near(m[1] * x + m[3] * y + m[5], ey, `my${i}`);
        });
    });
}

test("fitBox lấp đầy phần trong lề và giữ tỷ lệ (kể cả sau khi xoay)", () => {
    const inner = innerArea({ x: 0, y: 0, w: 210, h: 297 }, 5);
    const flat = fitBox(SRC, 0, inner);
    near(flat.w, 200, "w"); near(flat.h, 50, "h");
    const turned = fitBox(SRC, 90, inner);                 // 10 x 40 -> cao 287 thì rộng 71.75
    near(turned.h, 287, "h90"); near(turned.w, 71.75, "w90");
    assert.deepEqual(rotatedSize(SRC, 270), { w: 10, h: 40 });
});
