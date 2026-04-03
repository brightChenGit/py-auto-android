
from dataclasses import dataclass, field
from typing import List, Optional




@dataclass
class ClassNames:
    edit: str = "android.widget.EditText"
    LinearLayout: str = "android.widget.LinearLayout"



@dataclass
class DemoVoConfig:
    appName: str = "demo_vo"
    classNames: ClassNames = field(default_factory=ClassNames)