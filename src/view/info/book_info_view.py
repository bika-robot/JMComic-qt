from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, QSize, QEvent
from PySide6.QtGui import QColor, QFont, QPixmap, QIcon
from PySide6.QtWidgets import QListWidgetItem, QLabel

from config.setting import Setting
from interface.ui_book_info import Ui_BookInfo
from qt_owner import QtOwner
from server import req, ToolUtil, config, Status
from task.qt_task import QtTaskBase
from tools.book import BookMgr, BookInfo
from tools.str import Str


class BookInfoView(QtWidgets.QWidget, Ui_BookInfo, QtTaskBase):
    def __init__(self):
        super(self.__class__, self).__init__()
        Ui_BookInfo.__init__(self)
        QtTaskBase.__init__(self)
        self.setupUi(self)
        self.bookId = ""
        self.url = ""
        self.path = ""
        self.bookName = ""
        self.lastEpsId = -1
        self.lastIndex = 0
        self.pictureData = None
        self.isFavorite = False
        self.isLike = False

        self.picture.installEventFilter(self)
        self.title.setWordWrap(True)
        self.title.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.autorList.itemClicked.connect(self.ClickAutorItem)
        self.idLabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.description.setTextInteractionFlags(Qt.TextBrowserInteraction)

        self.downloadButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.downloadButton.setIconSize(QSize(50, 50))
        self.favoriteButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.favoriteButton.setIconSize(QSize(50, 50))
        self.commentButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.commentButton.setIconSize(QSize(50, 50))
        self.description.adjustSize()
        self.title.adjustSize()

        self.tagsList.itemClicked.connect(self.ClickTagsItem)

        self.epsListWidget.setFlow(self.epsListWidget.LeftToRight)
        self.epsListWidget.setWrapping(True)
        self.epsListWidget.setFrameShape(self.epsListWidget.NoFrame)
        self.epsListWidget.setResizeMode(self.epsListWidget.Adjust)

        self.epsListWidget.clicked.connect(self.OpenReadImg)

        # QScroller.grabGesture(self.epsListWidget, QScroller.LeftMouseButtonGesture)
        # self.epsListWidget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        # self.epsListWidget.verticalScrollBar().setStyleSheet(QssDataMgr().GetData('qt_list_scrollbar'))
        # self.epsListWidget.verticalScrollBar().setSingleStep(30)
        self.userIconData = None

        # self.epsListWidget.verticalScrollBar().rangeChanged.connect(self.ChageMaxNum)
        self.epsListWidget.setMinimumHeight(300)

    def UpdateFavoriteIcon(self):
        p = QPixmap()
        if self.isFavorite:
            self.favoriteButton.setIcon(QIcon(":/png/icon/icon_like.png"))
        else:
            self.favoriteButton.setIcon(QIcon(":/png/icon/icon_like_off.png"))

    def Clear(self):
        self.ClearTask()
        self.epsListWidget.clear()

    def SwitchCurrent(self, **kwargs):
        bookId = kwargs.get("bookId")
        if bookId:
            self.OpenBook(bookId)
        pass

    def OpenBook(self, bookId):
        self.bookId = bookId
        self.setFocus()
        self.Clear()
        self.show()
        QtOwner().ShowLoading()
        self.AddHttpTask(req.GetBookInfoReq(self.bookId), self.OpenBookBack)

    def OpenBookBack(self, raw):
        QtOwner().CloseLoading()
        self.tagsList.clear()
        self.autorList.clear()
        info = BookMgr().books.get(self.bookId)
        st = raw["st"]
        if info:
            isFavorite = raw.get('isFavorite')
            self.isFavorite = bool(isFavorite)
            assert isinstance(info, BookInfo)
            for author in info.baseInfo.authorList:
                self.autorList.AddItem(author)
            title = info.baseInfo.title
            if info.pageInfo.pages:
                title += "<font color=#d5577c>{}</font>".format("(" + str(info.pageInfo.pages) + "P)")
            self.title.setText(title)
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            self.title.setFont(font)
            self.idLabel.setText(info.baseInfo.id)

            self.bookName = info.baseInfo.title
            self.description.setPlainText(info.pageInfo.des)

            # for name in info.categories:
            #     self.categoriesList.AddItem(name)
            for name in info.baseInfo.tagList:
                self.tagsList.AddItem(name)
            # self.starButton.setText(str(info.totalLikes))
            # self.views.setText(str(info.totalViews))
            # self.isFavorite = info.isFavourite
            # self.isLike = info.isLiked
            self.UpdateFavoriteIcon()
            self.picture.setText(Str.GetStr(Str.LoadingPicture))
            self.url = info.baseInfo.coverUrl
            self.path = "{}_cover".format(self.bookId)
            # dayStr = ToolUtil.GetUpdateStr(info.pageInfo.createDate)
            # self.updateTick.setText(str(dayStr) + Str.GetStr(Str.Updated))
            if config.IsLoadingPicture:
                self.AddDownloadTask(self.url, self.path, completeCallBack=self.UpdatePicture)
            self.UpdateEpsData()
        else:
            # QtWidgets.QMessageBox.information(self, '加载失败', msg, QtWidgets.QMessageBox.Yes)
            QtOwner().ShowError(Str.GetStr(st))

        # if st == Status.UnderReviewBook:
        #     QtOwner().ShowError(Str.GetStr(st))

        return

    def LoadingPictureComplete(self, data, status):
        if status == Status.Ok:
            self.userIconData = data
            self.user_icon.SetPicture(data)

    def UpdatePicture(self, data, status):
        if status == Status.Ok:
            self.pictureData = data
            pic = QtGui.QPixmap()
            pic.loadFromData(data)
            radio = self.devicePixelRatio()
            pic.setDevicePixelRatio(radio)
            newPic = pic.scaled(self.picture.size()*radio, QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.picture.setPixmap(newPic)
            # self.picture.setScaledContents(True)
            if Setting.CoverIsOpenWaifu.value:
                w, h = ToolUtil.GetPictureSize(self.pictureData)
                if max(w, h) <= Setting.CoverMaxNum.value:
                    model = ToolUtil.GetModelByIndex(Setting.CoverLookNoise.value, Setting.CoverLookScale.value, Setting.CoverLookModel.value)
                    self.AddConvertTask(self.path, self.pictureData, model, self.Waifu2xPictureBack)
        else:
            self.picture.setText(Str.GetStr(Str.LoadingFail))
        return

    def Waifu2xPictureBack(self, data, waifuId, index, tick):
        if data:
            pic = QtGui.QPixmap()
            pic.loadFromData(data)
            radio = self.devicePixelRatio()
            pic.setDevicePixelRatio(radio)
            newPic = pic.scaled(self.picture.size()*radio, QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.picture.setPixmap(newPic)
        return

    def GetEpsBack(self, raw):
        st = raw["st"]
        if st == Status.Ok:
            self.UpdateEpsData()
            self.lastEpsId = -1
            self.LoadHistory()
            return
        else:
            QtOwner().ShowError(Str.GetStr(Str.ChapterLoadFail) + ", {}".format(Str.GetStr(st)))
        return

    def UpdateEpsData(self):
        self.epsListWidget.clear()
        info = BookMgr().books.get(self.bookId)
        if not info:
            return
        assert isinstance(info, BookInfo)
        self.startRead.setEnabled(True)
        # downloadIds = QtOwner().owner.downloadForm.GetDownloadCompleteEpsId(self.bookId)
        for index in sorted(info.pageInfo.epsInfo.keys()):
            epsInfo = info.pageInfo.epsInfo.get(index)
            label = QLabel(str(index+1) + "-" + epsInfo.title)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: rgb(196, 95, 125);")
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            label.setFont(font)
            # label.setWordWrap(True)
            # label.setContentsMargins(20, 10, 20, 10)
            item = QListWidgetItem(self.epsListWidget)
            # if index in downloadIds:
            #     item.setBackground(QColor(18, 161, 130))
            # else:
            #     item.setBackground(QColor(0, 0, 0, 0))
            item.setSizeHint(label.sizeHint() + QSize(20, 20))
            item.setToolTip(epsInfo.title)
            self.epsListWidget.setItemWidget(item, label)

        return

    # def ChageMaxNum(self):
    #     maxHeight = self.epsListWidget.verticalScrollBar().maximum()
    #     print(maxHeight)
    #     self.epsListWidget.setMinimumHeight(maxHeight)

    def AddDownload(self):
        QtOwner().OpenEpsInfo(self.bookId)
        return

    def AddFavorite(self):
        if not config.LoginUserName:
            QtOwner().ShowError(Str.GetStr(Str.NotLogin))
            return
        if self.isFavorite:
            self.AddHttpTask(req.DelFavoritesReq(self.bookId), self.DelFavoriteBack)
        else:
            self.AddHttpTask(req.AddFavoritesReq(self.bookId), self.AddFavoriteBack)

    def DelFavoriteBack(self, raw):
        if not config.LoginUserName:
            QtOwner().ShowError(Str.GetStr(Str.NotLogin))
            return
        st = raw["st"]
        if st == Status.Ok:
            self.isFavorite = False
            self.UpdateFavoriteIcon()
            QtOwner().ShowMsg(Str.GetStr(Str.DelFavoriteSuc))
        else:
            QtOwner().ShowError(Str.GetStr(st))

    def AddFavoriteBack(self, raw):
        st = raw["st"]
        if st == Status.Ok:
            self.isFavorite = True
            self.UpdateFavoriteIcon()
            QtOwner().ShowMsg(Str.GetStr(Str.AddFavoriteSuc))
        else:
            QtOwner().ShowError(Str.GetStr(st))

    def OpenReadImg(self, modelIndex):
        index = modelIndex.row()
        self.OpenReadIndex(index)

    def OpenReadIndex(self, index, pageIndex=-1):
        item = self.epsListWidget.item(index)
        if not item:
            return
        widget = self.epsListWidget.itemWidget(item)
        if not widget:
            return
        name = widget.text()
        QtOwner().OpenReadView(self.bookId, index, name, pageIndex=pageIndex)
        # self.stackedWidget.setCurrentIndex(1)

    def StartRead(self):
        if self.lastEpsId >= 0:
            self.OpenReadIndex(self.lastEpsId, self.lastIndex)
        else:
            self.OpenReadIndex(0)
        return

    def LoadHistory(self):
        return
        info = QtOwner().historyView.GetHistory(self.bookId)
        if not info:
            self.startRead.setText(Str.GetStr(Str.LookFirst))
            return
        if self.lastEpsId == info.epsId:
            self.lastIndex = info.picIndex
            self.startRead.setText(Str.GetStr(Str.LastLook) + str(self.lastEpsId + 1) + Str.GetStr(Str.Chapter) + str(info.picIndex + 1) + Str.GetStr(Str.Page))
            return

        if self.lastEpsId >= 0:
            item = self.epsListWidget.item(self.lastEpsId)
            if item:
                downloadIds = QtOwner().downloadView.GetDownloadCompleteEpsId(self.bookId)
                if self.lastEpsId in downloadIds:
                    item.setBackground(QColor(18, 161, 130))
                else:
                    item.setBackground(QColor(0, 0, 0, 0))

        item = self.epsListWidget.item(info.epsId)
        if not item:
            return
        item.setBackground(QColor(238, 162, 164))
        self.lastEpsId = info.epsId
        self.lastIndex = info.picIndex
        self.startRead.setText(Str.GetStr(Str.LastLook) + str(self.lastEpsId + 1) + Str.GetStr(Str.Chapter) + str(info.picIndex + 1) + Str.GetStr(Str.Page))

    def ClickAutorItem(self, item):
        text = item.text()
        # QtOwner().owner.searchForm.SearchAutor(text)
        QtOwner().OpenSearch(text)
        return

    def ClickTagsItem(self, item):
        text = item.text()
        # QtOwner().owner.searchForm.SearchTags(text)
        QtOwner().OpenSearch(text)
        return

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                if obj == self.picture:
                    if self.pictureData:
                        QtOwner().OpenWaifu2xTool(self.pictureData)
                # elif obj == self.user_name:
                #     QtOwner().owner.searchForm.SearchCreator(self.user_name.text())
                return True
            else:
                return False
        else:
            return super(self.__class__, self).eventFilter(obj, event)

    def keyPressEvent(self, ev):
        key = ev.key()
        if Qt.Key_Escape == key:
            self.close()
        return super(self.__class__, self).keyPressEvent(ev)