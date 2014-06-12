from sqlalchemy import Column, Integer, String, Text, Boolean, Date, \
    ForeignKey
from sqlalchemy.orm import relationship, backref

from basemodel import Base, engine, Serializer
from picture_like import PictureLike
from picture_comment import PictureComment

class Picture(Base, Serializer):
    __tablename__ = 'pictures'
    __table_args__ = {'extend_existing':True}
    __public__ = ['id', 'album_id', 'original_url', 'resized_url',
        'likes', 'comments']

    id = Column(Integer, primary_key=True)
    album_id = Column(Integer, ForeignKey("albums.id"))
    original_url = Column(Text, default='')
    resized_url = Column(Text, default='')
    enlarged_url = Column(Text, default='')
    likes = relationship("PictureLike")
    comments = relationship("PictureComment")

    def __init__(self, album_id, original_url,
                 resized_url, enlarged_url):
        self.album_id = album_id
        self.original_url = original_url
        self.resized_url = resized_url
        self.enlarged_url = enlarged_url


    def __repr__(self):
       return "<Picture('%s', '%s', '%s, %s')>" % (self.original_url, self.resized_url, self.album_id, self.enlarged_url)


metadata = Base.metadata


if __name__ == "__main__":
    metadata.create_all(engine)
